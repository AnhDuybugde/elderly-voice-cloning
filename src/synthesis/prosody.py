"""Prosody / timing manipulation on WORLD frame sequences.

Elderly speech is slower *and* pauses more. Instead of a uniform time-stretch,
we build a non-uniform time map: phonated frames advance at `tempo_scale`
source-frames per output frame, while interior pauses advance at
`tempo_scale / pause_scale` (i.e. pauses are stretched more than speech).
Leading / trailing silence is copied 1:1.

Working on WORLD parameters (f0 / spectral envelope / aperiodicity) means the
stretch never touches pitch or timbre - no phase-vocoder "metallic" artefacts.
"""

from __future__ import annotations

import numpy as np


def frame_energy_db(x: np.ndarray, sr: int, n_frames: int, frame_period_ms: float) -> np.ndarray:
    """RMS energy (dB re. max) of the waveform around each WORLD frame centre."""
    hop = sr * frame_period_ms / 1000.0
    half = int(hop)  # 2 hops wide analysis window
    centers = (np.arange(n_frames) * hop).astype(int)
    e = np.empty(n_frames)
    for i, c in enumerate(centers):
        seg = x[max(0, c - half) : c + half]
        e[i] = np.sqrt(np.mean(seg**2)) if len(seg) else 0.0
    return 20.0 * np.log10(e / (np.max(e) + 1e-12) + 1e-12)


def find_pause_frames(
    energy_db: np.ndarray,
    voiced: np.ndarray,
    frame_period_ms: float,
    threshold_db: float = -40.0,
    min_pause_ms: float = 90.0,
) -> tuple[np.ndarray, int, int]:
    """Return (interior_pause_mask, first_active, last_active)."""
    active = (energy_db > threshold_db) | voiced
    idx = np.flatnonzero(active)
    mask = np.zeros(len(energy_db), dtype=bool)
    if len(idx) == 0:
        return mask, 0, len(energy_db) - 1
    first, last = int(idx[0]), int(idx[-1])
    min_len = max(1, int(round(min_pause_ms / frame_period_ms)))

    run_start = None
    for i in range(first, last + 1):
        if not active[i]:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None and i - run_start >= min_len:
                mask[run_start:i] = True
            run_start = None
    return mask, first, last


def build_time_map(
    n_frames: int,
    pause_mask: np.ndarray,
    first_active: int,
    last_active: int,
    tempo_scale: float,
    pause_scale: float,
) -> np.ndarray:
    """Fractional source-frame positions for every output frame."""
    tempo_scale = float(np.clip(tempo_scale, 0.4, 1.6))
    pause_scale = float(np.clip(pause_scale, 0.5, 3.0))
    step = np.full(n_frames, tempo_scale)
    step[pause_mask] = tempo_scale / pause_scale
    step[:first_active] = 1.0
    step[last_active + 1 :] = 1.0

    positions = []
    pos = 0.0
    limit = n_frames - 1
    while pos <= limit:
        positions.append(pos)
        pos += step[min(int(pos), limit)]
    return np.asarray(positions, dtype=np.float64)


def resample_world_params(
    f0: np.ndarray,
    sp: np.ndarray,
    ap: np.ndarray,
    positions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate WORLD parameters at fractional frame positions.

    sp is interpolated in log domain; f0 is interpolated in log domain only
    between two voiced frames, otherwise the nearest frame's voicing wins.
    """
    n = len(f0)
    i0 = np.clip(np.floor(positions).astype(int), 0, n - 1)
    i1 = np.clip(i0 + 1, 0, n - 1)
    w = (positions - i0)[:, None]

    log_sp = np.log(np.maximum(sp, 1e-16))
    sp_out = np.exp((1.0 - w) * log_sp[i0] + w * log_sp[i1])
    ap_out = np.clip((1.0 - w) * ap[i0] + w * ap[i1], 0.0, 1.0)

    w1 = w[:, 0]
    f0a, f0b = f0[i0], f0[i1]
    both = (f0a > 0) & (f0b > 0)
    f0_out = np.where(w1 < 0.5, f0a, f0b).astype(np.float64)
    f0_out[both] = np.exp((1.0 - w1[both]) * np.log(f0a[both]) + w1[both] * np.log(f0b[both]))
    return f0_out, np.ascontiguousarray(sp_out), np.ascontiguousarray(ap_out)
