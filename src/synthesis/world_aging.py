"""WORLD-vocoder presbyphonia engine (v3.0).

The neural TTS output is decomposed with WORLD into
    f0  (harvest)        - pitch contour
    sp  (cheaptrick)     - spectral envelope  (vocal tract / formants)
    ap  (d4c)            - aperiodicity       (breathiness / noise)
and each physiological aging cue is applied to the component it belongs to:

    F0 level & range    -> f0   (log-domain shift + range scaling, keeps the 6 Vietnamese tones)
    jitter              -> f0   (short-correlated frame perturbation, voiced frames only)
    vocal tremor        -> f0 + sp (4-7 Hz, drifting rate + depth -> not a mechanical sine)
    shimmer             -> sp   (frame-level gain perturbation)
    breathiness         -> ap   (raised aperiodicity, frequency-weighted)
    vocal-tract change  -> sp   (formant frequency warp + steeper spectral tilt)
    vocal fry / breaks  -> f0 + ap + sp at phrase ends / random points
    tempo & pauses      -> frame time map (see prosody.py)

The result is re-synthesised once with WORLD, so no phase-vocoder artefacts.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyworld as pw
import scipy.signal as signal

from src.core.schema import VoiceAgingParams
from src.synthesis.prosody import (
    build_time_map,
    find_pause_frames,
    frame_energy_db,
    resample_world_params,
)

FRAME_PERIOD_MS = 5.0
FINE_FRAME_MS = 2.0  # synthesis grid when cycle-level jitter / shimmer is applied
F0_BOUNDS = {"nam": (55.0, 400.0), "nu": (90.0, 600.0)}
TARGET_RMS_DBFS = -20.0
PEAK_LIMIT = 0.89  # ~ -1 dBFS


# ---------------------------------------------------------------------------
# Random helpers
# ---------------------------------------------------------------------------
def _smooth_noise(rng: np.random.Generator, n: int, smooth_frames: int) -> np.ndarray:
    """Unit-variance low-pass noise (moving-average smoothed white noise)."""
    white = rng.standard_normal(n + 2 * smooth_frames)
    if smooth_frames > 1:
        kernel = np.hanning(2 * smooth_frames + 1)
        kernel /= kernel.sum()
        white = np.convolve(white, kernel, mode="same")
    out = white[smooth_frames : smooth_frames + n]
    std = np.std(out)
    return out / std if std > 1e-12 else out


def _voiced_segments(voiced: np.ndarray) -> list[tuple[int, int]]:
    """List of (start, end_exclusive) voiced runs."""
    segs = []
    start = None
    for i, v in enumerate(voiced):
        if v and start is None:
            start = i
        elif not v and start is not None:
            segs.append((start, i))
            start = None
    if start is not None:
        segs.append((start, len(voiced)))
    return segs


# ---------------------------------------------------------------------------
# Component manipulations
# ---------------------------------------------------------------------------
def _apply_f0_level_and_range(f0: np.ndarray, target_f0: float, range_scale: float) -> np.ndarray:
    voiced = f0 > 0
    if not np.any(voiced):
        return f0
    lf = np.log(f0[voiced])
    mu = np.mean(lf)
    target_mu = np.log(target_f0) if target_f0 > 0 else mu
    out = f0.copy()
    out[voiced] = np.exp(target_mu + range_scale * (lf - mu))
    return out


def _tremor_lfo(rng: np.random.Generator, n: int, rate_hz: float) -> np.ndarray:
    """Quasi-periodic tremor oscillator with drifting rate and depth (range ~[-1, 1])."""
    fps = 1000.0 / FRAME_PERIOD_MS
    rate = rate_hz + 0.35 * _smooth_noise(rng, n, int(fps * 0.4))
    rate = np.clip(rate, 3.5, 8.0)
    phase = rng.uniform(0, 2 * np.pi) + np.cumsum(2 * np.pi * rate / fps)
    depth_env = np.clip(0.75 + 0.25 * _smooth_noise(rng, n, int(fps * 0.6)), 0.3, 1.3)
    return np.sin(phase) * depth_env


def _apply_cycle_perturbation(
    f0: np.ndarray,
    sp: np.ndarray,
    rng: np.random.Generator,
    jitter_pct: float,
    shimmer_db: float,
    frame_ms: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Perturb F0 and amplitude once per glottal cycle (piecewise constant per cycle).

    Frame-level noise gets smoothed away by WORLD's per-sample F0 interpolation; holding
    one random value per pitch period is what makes Praat-measured jitter/shimmer rise.
    """
    voiced = f0 > 0
    phase = np.cumsum(np.where(voiced, f0, 0.0) * frame_ms / 1000.0)
    cycle = np.floor(phase).astype(int)
    n_cycles = int(cycle.max()) + 2 if len(cycle) else 1
    f0 = f0.copy()
    if jitter_pct > 0:
        jn = np.clip(rng.standard_normal(n_cycles), -3.0, 3.0)
        f0[voiced] *= 1.0 + (jitter_pct / 100.0) * jn[cycle[voiced]]
    if shimmer_db > 0:
        g = np.clip(rng.standard_normal(n_cycles), -3.0, 3.0) * shimmer_db
        g_frames = np.where(voiced, g[cycle], 0.0)
        sp = sp * (10.0 ** (g_frames / 10.0))[:, None]
    return f0, sp


def _warp_formants(sp: np.ndarray, alpha: float) -> np.ndarray:
    """Frequency-warp the spectral envelope. alpha<1 lowers formants."""
    if abs(alpha - 1.0) < 1e-4:
        return sp
    n_bins = sp.shape[1]
    src = np.clip(np.arange(n_bins) / alpha, 0, n_bins - 1)
    i0 = np.floor(src).astype(int)
    i1 = np.clip(i0 + 1, 0, n_bins - 1)
    w = src - i0
    log_sp = np.log(np.maximum(sp, 1e-16))
    return np.exp((1 - w) * log_sp[:, i0] + w * log_sp[:, i1])


def _tilt_gain(n_bins: int, sr: int, fft_size: int, tilt_db_oct: float) -> np.ndarray:
    freqs = np.arange(n_bins) * sr / fft_size
    gain_db = tilt_db_oct * np.log2(np.maximum(freqs, 500.0) / 500.0)
    return 10.0 ** (gain_db / 10.0)  # sp is a power spectrum


def _breath_weight(n_bins: int, sr: int, fft_size: int) -> np.ndarray:
    """Aperiodicity raise weight: partial below 500 Hz (glottal leak), full above 2.5 kHz."""
    freqs = np.arange(n_bins) * sr / fft_size
    return 0.3 + 0.7 * np.clip((freqs - 500.0) / 2000.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Post-processing (light analog colour + loudness)
# ---------------------------------------------------------------------------
def _post_process(y: np.ndarray, sr: int, params: VoiceAgingParams) -> np.ndarray:
    nyq = sr / 2.0
    if params.chest_warmth > 0:
        b, a = signal.iirpeak(300.0 / nyq, Q=1.2)
        y = y + params.chest_warmth * signal.lfilter(b, a, y)
    if params.hf_cutoff_hz and params.hf_cutoff_hz < nyq * 0.95:
        sos = signal.butter(2, params.hf_cutoff_hz / nyq, btype="low", output="sos")
        y = signal.sosfiltfilt(sos, y)
    # DC / rumble removal
    sos_hp = signal.butter(2, 50.0 / nyq, btype="high", output="sos")
    y = signal.sosfiltfilt(sos_hp, y)
    return normalize_loudness(y)


def normalize_loudness(y: np.ndarray, target_rms_dbfs: float = TARGET_RMS_DBFS) -> np.ndarray:
    """Normalize RMS of the active (non-silent) part, then limit the peak."""
    y = np.asarray(y, dtype=np.float64)
    if len(y) == 0 or np.max(np.abs(y)) < 1e-8:
        return y.astype(np.float32)
    frame = 1024
    n = len(y) // frame
    if n >= 4:
        rms = np.sqrt(np.mean(y[: n * frame].reshape(n, frame) ** 2, axis=1))
        active = rms[rms > np.max(rms) * 0.05]
        level = np.sqrt(np.mean(active**2)) if len(active) else np.sqrt(np.mean(y**2))
    else:
        level = np.sqrt(np.mean(y**2))
    y = y * (10 ** (target_rms_dbfs / 20.0) / (level + 1e-12))
    peak = np.max(np.abs(y))
    if peak > PEAK_LIMIT:
        y = y * (PEAK_LIMIT / peak)
    return y.astype(np.float32)


def _make_inhale(rng: np.random.Generator, sr: int, level_rms: float) -> np.ndarray:
    """Short audible in-breath: band-limited noise with an asymmetric envelope."""
    dur = rng.uniform(0.28, 0.48)
    n = int(dur * sr)
    noise = rng.standard_normal(n)
    sos = signal.butter(2, [500.0 / (sr / 2), 2600.0 / (sr / 2)], btype="band", output="sos")
    noise = signal.sosfilt(sos, noise)
    t = np.linspace(0, 1, n)
    env = np.where(t < 0.6, (t / 0.6) ** 1.5, ((1 - t) / 0.4) ** 0.8)
    breath = noise * env
    breath *= level_rms / (np.sqrt(np.mean(breath**2)) + 1e-12)
    gap = np.zeros(int(rng.uniform(0.08, 0.16) * sr))
    return np.concatenate([breath, gap])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def age_voice(
    audio: np.ndarray,
    sr: int,
    params: VoiceAgingParams,
    rng: Optional[np.random.Generator] = None,
    gender: Optional[str] = None,
    return_info: bool = False,
):
    """Apply physiological aging to a clean speech signal.

    Args:
        audio: mono float waveform.
        sr: sample rate.
        params: resolved per-utterance DSP parameters.
        rng: random generator (seed it for reproducible output).
        gender: "nam" | "nu" (selects F0 analysis bounds).
        return_info: also return a dict describing the random events applied.
    """
    rng = rng if rng is not None else np.random.default_rng()
    info = {"n_creaks": 0, "n_breaks": 0, "inhale": False, "src_f0_hz": 0.0, "out_frames_ratio": 1.0}

    x = np.asarray(audio, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if len(x) < int(0.1 * sr) or np.max(np.abs(x)) < 1e-6:
        y = x.astype(np.float32)
        return (y, info) if return_info else y

    x = x / (np.max(np.abs(x)) + 1e-12) * 0.8
    floor, ceil = F0_BOUNDS.get(gender, (60.0, 500.0))

    # --- 1. WORLD analysis ---
    f0, t = pw.harvest(x, sr, f0_floor=floor, f0_ceil=ceil, frame_period=FRAME_PERIOD_MS)
    sp = pw.cheaptrick(x, f0, t, sr)
    ap = pw.d4c(x, f0, t, sr)
    fft_size = (sp.shape[1] - 1) * 2
    if np.any(f0 > 0):
        info["src_f0_hz"] = float(np.exp(np.median(np.log(f0[f0 > 0]))))

    # --- 2. Timing: tempo + pause stretching ---
    energy = frame_energy_db(x, sr, len(f0), FRAME_PERIOD_MS)
    pause_mask, first, last = find_pause_frames(energy, f0 > 0, FRAME_PERIOD_MS)
    if abs(params.tempo_scale - 1.0) > 1e-3 or abs(params.pause_scale - 1.0) > 1e-3:
        positions = build_time_map(len(f0), pause_mask, first, last, params.tempo_scale, params.pause_scale)
        info["out_frames_ratio"] = len(positions) / len(f0)
        f0, sp, ap = resample_world_params(f0, sp, ap, positions)

    n = len(f0)
    voiced = f0 > 0
    sp = sp.copy()
    ap = ap.copy()

    # --- 3. F0 level & intonation range ---
    f0 = _apply_f0_level_and_range(f0, params.target_f0_hz, params.f0_range_scale)

    # --- 4. Vocal tremor (F0 + amplitude) ---
    if params.tremor_f0_depth > 0 or params.tremor_amp_depth > 0:
        lfo = _tremor_lfo(rng, n, params.tremor_rate_hz)
        f0[voiced] *= 1.0 + params.tremor_f0_depth * lfo[voiced]
        amp = 1.0 + params.tremor_amp_depth * np.roll(lfo, 3)
        sp *= (amp**2)[:, None]

    # --- 5. Breathiness / hoarseness (aperiodicity) ---
    if params.breathiness > 0:
        w = _breath_weight(sp.shape[1], sr, fft_size)
        # Slowly varying breathiness: elderly airflow is not constant
        b_env = np.clip(params.breathiness * (1.0 + 0.25 * _smooth_noise(rng, n, 40)), 0.0, 0.95)
        raise_ = (b_env[:, None] * w[None, :]) * (1.0 - ap)
        ap[voiced] = ap[voiced] + raise_[voiced]

    # --- 6. Vocal fry at phrase ends ---
    segments = _voiced_segments(voiced)
    if params.creak_prob > 0:
        for s, e in segments:
            seg_len = e - s
            followed_by_pause = e >= n - 1 or not np.any(voiced[e : min(n, e + 20)])
            if seg_len < 16 or not followed_by_pause or rng.random() > params.creak_prob:
                continue
            L = int(min(seg_len * 0.4, rng.uniform(16, 32)))
            ramp = np.linspace(0.0, 1.0, L) ** 1.3
            drop = rng.uniform(0.45, 0.65)
            sl = slice(e - L, e)
            f0[sl] *= 1.0 - (1.0 - drop) * ramp
            f0[sl] *= 1.0 + 0.06 * ramp * rng.standard_normal(L)
            ap[sl] = np.clip(ap[sl] + (0.25 * ramp)[:, None], 0.0, 1.0)
            sp[sl] *= ((1.0 - 0.45 * ramp) ** 2)[:, None]
            info["n_creaks"] += 1

    # --- 7. Brief phonation breaks (pitch breaks / breathy dropouts) ---
    if params.voice_break_prob > 0:
        voiced_sec = voiced.sum() * FRAME_PERIOD_MS / 1000.0
        n_breaks = rng.poisson(params.voice_break_prob * voiced_sec)
        long_segs = [(s, e) for s, e in segments if e - s >= 40]
        for _ in range(min(n_breaks, len(long_segs))):
            s, e = long_segs[rng.integers(len(long_segs))]
            c = int(rng.integers(s + 12, e - 12))
            L = int(rng.integers(5, 10))
            sl = slice(c, c + L)
            win = np.hanning(L)
            f0[sl] *= 1.0 - rng.uniform(0.12, 0.25) * win
            ap[sl] = np.clip(ap[sl] + (0.5 * win)[:, None], 0.0, 1.0)
            sp[sl] *= ((1.0 - 0.5 * win) ** 2)[:, None]
            info["n_breaks"] += 1

    # --- 8. Vocal tract: formant warp + spectral tilt ---
    sp = _warp_formants(sp, params.formant_warp)
    if abs(params.spectral_tilt_db_oct) > 1e-3:
        sp *= _tilt_gain(sp.shape[1], sr, fft_size, params.spectral_tilt_db_oct)[None, :]

    # --- 9. Cycle-level jitter & shimmer on a fine (2 ms) frame grid ---
    synth_period = FRAME_PERIOD_MS
    if params.jitter_pct > 0 or params.shimmer_db > 0:
        up = FRAME_PERIOD_MS / FINE_FRAME_MS
        positions = np.arange(0, n - 1 + 1e-9, 1.0 / up)
        f0, sp, ap = resample_world_params(f0, sp, ap, positions)
        f0, sp = _apply_cycle_perturbation(f0, sp, rng, params.jitter_pct, params.shimmer_db, FINE_FRAME_MS)
        synth_period = FINE_FRAME_MS
        voiced = f0 > 0

    # --- 10. Re-synthesis ---
    f0 = np.where(voiced, np.clip(f0, floor * 0.8, ceil), 0.0)
    y = pw.synthesize(
        np.ascontiguousarray(f0), np.ascontiguousarray(sp), np.ascontiguousarray(np.clip(ap, 0.0, 1.0)),
        sr, synth_period,
    )

    # --- 11. Audible inhale before the utterance ---
    if params.inhale_prob > 0 and rng.random() < params.inhale_prob:
        speech_rms = np.sqrt(np.mean(y**2))
        inhale = _make_inhale(rng, sr, speech_rms * 10 ** (-24.0 / 20.0))
        lead_frames = int(np.argmax(np.abs(y) > 0.02 * np.max(np.abs(y))))
        head = y[:lead_frames]
        y = np.concatenate([head[: int(0.05 * sr)], inhale, y[lead_frames:]])
        info["inhale"] = True

    y = _post_process(y, sr, params)
    return (y, info) if return_info else y
