"""Acoustic feature extraction (v3.0) backed by Praat via Parselmouth.

Measures what clinical voice labs measure for presbyphonia:
- F0 statistics (mean / std / range), gender-aware pitch floor & ceiling
- Local jitter and local shimmer from a periodic PointProcess
- HNR (cross-correlation harmonicity)
- CPPS (smoothed cepstral peak prominence) - sensitive to breathiness / hoarseness
- Temporal metrics: speech rate (Vietnamese syllables per second of phonation),
  pause ratio and mean pause duration from an energy VAD

The legacy v2 helpers (`extract_f0_statistics`, `compute_jitter_shimmer`,
`compute_hnr`) are kept as thin wrappers so older call sites keep working.
"""

from __future__ import annotations

import math
import re
from typing import Optional

import numpy as np

try:  # Parselmouth is the reference measurement backend
    import parselmouth
    from parselmouth.praat import call as praat_call

    _HAS_PRAAT = True
except Exception:  # pragma: no cover - only hit when dependency missing
    parselmouth = None
    praat_call = None
    _HAS_PRAAT = False

# Pitch analysis bounds per gender (Praat recommendations for adult voices)
PITCH_BOUNDS = {
    "nam": (60.0, 300.0),
    "nu": (100.0, 500.0),
    None: (65.0, 450.0),
}

_ZERO_RESULT = {
    "f0_mean_hz": 0.0,
    "f0_std_hz": 0.0,
    "f0_min_hz": 0.0,
    "f0_max_hz": 0.0,
    "voiced_ratio": 0.0,
}


def _sound(audio: np.ndarray, sr: int):
    return parselmouth.Sound(np.asarray(audio, dtype=np.float64), sampling_frequency=float(sr))


def _nan_to(value: float, default: float = 0.0) -> float:
    if value is None or not math.isfinite(value):
        return default
    return float(value)


# ---------------------------------------------------------------------------
# Voice quality (Praat)
# ---------------------------------------------------------------------------
def measure_voice_quality(
    audio: np.ndarray,
    sr: int,
    gender: Optional[str] = None,
) -> dict[str, float]:
    """Praat-standard F0 / jitter / shimmer / HNR / CPPS measurements."""
    floor, ceiling = PITCH_BOUNDS.get(gender, PITCH_BOUNDS[None])
    out = dict(_ZERO_RESULT)
    out.update({"jitter_pct": 0.0, "shimmer_pct": 0.0, "hnr_db": 0.0, "cpps_db": 0.0})

    if not _HAS_PRAAT or len(audio) < int(0.2 * sr) or np.max(np.abs(audio)) < 1e-5:
        return out

    snd = _sound(audio, sr)

    # --- F0 ---
    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=floor, pitch_ceiling=ceiling)
    f0 = pitch.selected_array["frequency"]
    voiced = f0[f0 > 0]
    if len(voiced) > 0:
        out.update(
            {
                "f0_mean_hz": float(np.mean(voiced)),
                "f0_std_hz": float(np.std(voiced)),
                "f0_min_hz": float(np.percentile(voiced, 5)),
                "f0_max_hz": float(np.percentile(voiced, 95)),
                "voiced_ratio": float(len(voiced) / max(len(f0), 1)),
            }
        )
    else:
        return out

    # --- Jitter / shimmer from glottal pulses ---
    try:
        pp = praat_call(snd, "To PointProcess (periodic, cc)", floor, ceiling)
        jitter = praat_call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = praat_call([snd, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        out["jitter_pct"] = _nan_to(jitter) * 100.0
        out["shimmer_pct"] = _nan_to(shimmer) * 100.0
    except Exception:
        pass

    # --- HNR ---
    try:
        harm = praat_call(snd, "To Harmonicity (cc)", 0.01, floor, 0.1, 1.0)
        out["hnr_db"] = _nan_to(praat_call(harm, "Get mean", 0, 0))
    except Exception:
        pass

    # --- CPPS ---
    try:
        snd16 = snd.resample(16000) if sr > 16000 else snd
        pcg = praat_call(snd16, "To PowerCepstrogram", 60.0, 0.002, 5000.0, 50.0)
        cpps = praat_call(
            pcg, "Get CPPS", "no", 0.02, 0.0005, 60.0, 330.0, 0.05,
            "Parabolic", 0.001, 0.0, "Straight", "Robust",
        )
        out["cpps_db"] = _nan_to(cpps)
    except Exception:
        pass

    return out


# ---------------------------------------------------------------------------
# Temporal metrics
# ---------------------------------------------------------------------------
def count_vi_syllables(text: str) -> int:
    """Vietnamese is monosyllabic per written word: count word tokens."""
    if not text:
        return 0
    tokens = re.findall(r"[^\W\d_]+|\d+", text, flags=re.UNICODE)
    return len(tokens)


def speech_activity(
    audio: np.ndarray,
    sr: int,
    frame_ms: float = 20.0,
    threshold_db: float = -38.0,
    min_pause_ms: float = 150.0,
) -> dict[str, float]:
    """Energy VAD: active speech time, pause ratio and mean pause length.

    Leading/trailing silence is excluded so the pause ratio reflects
    within-utterance pauses only.
    """
    hop = max(1, int(sr * frame_ms / 1000.0))
    n = len(audio) // hop
    if n < 3:
        return {"active_sec": 0.0, "pause_ratio": 0.0, "mean_pause_ms": 0.0, "n_pauses": 0}

    frames = np.asarray(audio[: n * hop], dtype=np.float64).reshape(n, hop)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms / (np.max(rms) + 1e-12))
    active = db > threshold_db

    idx = np.flatnonzero(active)
    if len(idx) == 0:
        return {"active_sec": 0.0, "pause_ratio": 0.0, "mean_pause_ms": 0.0, "n_pauses": 0}

    core = active[idx[0] : idx[-1] + 1]
    min_pause_frames = max(1, int(round(min_pause_ms / frame_ms)))

    pauses = []
    run = 0
    for a in core:
        if not a:
            run += 1
        else:
            if run >= min_pause_frames:
                pauses.append(run)
            run = 0

    pause_frames = int(sum(pauses))
    total_frames = len(core)
    speech_frames = total_frames - pause_frames
    return {
        "active_sec": speech_frames * frame_ms / 1000.0,
        "pause_ratio": pause_frames / max(total_frames, 1),
        "mean_pause_ms": float(np.mean(pauses) * frame_ms) if pauses else 0.0,
        "n_pauses": len(pauses),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyze_audio_sample(
    audio: np.ndarray,
    sr: int,
    gender: Optional[str] = None,
    text: Optional[str] = None,
) -> dict[str, float]:
    """Run full acoustic analysis on an audio buffer."""
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    vq = measure_voice_quality(audio, sr, gender)
    act = speech_activity(audio, sr)
    n_syl = count_vi_syllables(text) if text else 0
    rate = n_syl / act["active_sec"] if (n_syl and act["active_sec"] > 0) else 0.0

    return {
        "duration_sec": round(len(audio) / sr, 3),
        "f0_mean_hz": round(vq["f0_mean_hz"], 2),
        "f0_std_hz": round(vq["f0_std_hz"], 2),
        "f0_min_hz": round(vq["f0_min_hz"], 2),
        "f0_max_hz": round(vq["f0_max_hz"], 2),
        "voiced_ratio": round(vq["voiced_ratio"], 3),
        "jitter_pct": round(vq["jitter_pct"], 3),
        "shimmer_pct": round(vq["shimmer_pct"], 3),
        "hnr_db": round(vq["hnr_db"], 2),
        "cpps_db": round(vq["cpps_db"], 2),
        "speech_rate_syl_s": round(rate, 3),
        "pause_ratio": round(act["pause_ratio"], 3),
        "mean_pause_ms": round(act["mean_pause_ms"], 1),
        "peak_dbfs": round(20.0 * np.log10(np.max(np.abs(audio)) + 1e-12), 2),
    }


# ---------------------------------------------------------------------------
# Backward-compatible wrappers (v2 API)
# ---------------------------------------------------------------------------
def extract_f0_statistics(audio: np.ndarray, sr: int, fmin: float = 65.0, fmax: float = 300.0) -> dict[str, float]:
    vq = measure_voice_quality(audio, sr)
    return {k: vq[k] for k in _ZERO_RESULT}


def compute_jitter_shimmer(audio: np.ndarray, sr: int, f0_mean: float = 0.0) -> tuple[float, float]:
    vq = measure_voice_quality(audio, sr)
    return vq["jitter_pct"], vq["shimmer_pct"]


def compute_hnr(audio: np.ndarray, sr: int) -> float:
    return measure_voice_quality(audio, sr)["hnr_db"]
