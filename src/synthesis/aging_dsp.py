"""Acoustic enhancer and organic aging processor.

v3.0: `apply_aging_v3` / `apply_presbyphonia` route to the WORLD engine (world_aging.py).
`apply_analog_warmth_and_aging` is the original v2 EQ-only processor, kept unchanged for reference.

Upgraded to prevent metallic/robotic phase-vocoder artifacts:
- Uses subtle biquad acoustic equalization for chest resonance and vocal tract maturity
- Natural 1st-order high-frequency softening (avoids harsh artificial rolloff)
- Soft analog saturation for organic warmth and warmth rounding
- Organic micro-tremor using band-limited pink noise instead of harsh sine waves
- Headroom normalization avoiding digital clipping
"""

from __future__ import annotations

import numpy as np
import scipy.signal as signal

from src.core.schema import AcousticAgingParams


def apply_analog_warmth_and_aging(
    audio: np.ndarray,
    sr: int = 48000,
    age: int = 65,
) -> np.ndarray:
    """Enhances naturalness and applies subtle physiological aging cues without phase distortion.

    Args:
        audio: 1D float32 audio array.
        sr: Sample rate in Hz (default 48000).
        age: Age of the speaker in years.

    Returns:
        1D float32 enhanced audio array.
    """
    if len(audio) == 0:
        return audio

    y = audio.astype(np.float32).copy()
    nyquist = sr / 2.0

    # 1. Low-mid chest resonance warmth (peaking biquad at 280 Hz - 340 Hz)
    # Older individuals have deeper chest cavity resonance
    center_freq = 300.0 / nyquist
    if center_freq < 0.9:
        b_warm, a_warm = signal.iirpeak(center_freq, Q=1.2)
        warm_component = signal.lfilter(b_warm, a_warm, y)
        warm_gain = 0.12 if age < 70 else 0.18
        y = y + warm_gain * warm_component

    # 2. Gentle organic high-frequency softening (smooth 1st order shelf)
    # Prevents harsh modern microphone sizzle and simulates mature vocal fold damping
    if age >= 60:
        cutoff_hz = max(5500.0, 8500.0 - (age - 60) * 110.0)
        norm_cutoff = min(cutoff_hz / nyquist, 0.95)
        b_shelf, a_shelf = signal.butter(1, norm_cutoff, btype="low")
        y = signal.lfilter(b_shelf, a_shelf, y)

    # 3. Organic physiological micro-tremor for 75+ (using filtered random walk, NOT pure sine)
    if age >= 75:
        n_samples = len(y)
        # Generate random walk / pink noise
        white = np.random.normal(0, 1.0, size=n_samples)
        # Bandpass filter around 4.5 - 6.0 Hz
        low_t = 4.0 / nyquist
        high_t = 6.5 / nyquist
        b_trem, a_trem = signal.butter(2, [low_t, high_t], btype="band")
        organic_tremor = signal.lfilter(b_trem, a_trem, white)
        # Normalize tremor amplitude to very subtle depth (0.015 - 0.035)
        trem_depth = 0.02 if age < 80 else 0.035
        tremor_env = 1.0 + trem_depth * (organic_tremor / (np.max(np.abs(organic_tremor)) + 1e-8))
        y = y * tremor_env.astype(np.float32)

    # 4. Analog warmth soft saturation (smooths transients, adds subtle harmonic body)
    drive = 1.08 if age < 70 else 1.14
    y = np.tanh(y * drive) / drive

    # 5. Normalization with safe headroom (-1.5 dBFS)
    peak = np.max(np.abs(y))
    if peak > 1e-5:
        target_peak = 0.84  # -1.5 dBFS
        y = (y / peak) * target_peak

    return y.astype(np.float32)


def apply_aging_v3(
    audio: np.ndarray,
    sr: int = 48000,
    age: int = 65,
    gender: str = "nam",
    keep_length: bool = True,
    seed: int | None = 0,
) -> np.ndarray:
    """v3.0 WORLD aging with age-bin defaults (no speaker fingerprint, no tempo change).

    For full per-speaker / per-tone control use
    `src.synthesis.voice_profile.resolve_aging_params` + `src.synthesis.world_aging.age_voice`.
    """
    from src.synthesis.voice_profile import age_bin_for, get_profile
    from src.synthesis.world_aging import age_voice
    from src.core.schema import VoiceAgingParams

    prof = get_profile(gender, age_bin_for(age))
    dsp = dict(prof["dsp"])
    params = VoiceAgingParams(
        target_f0_hz=0.0,
        jitter_pct=dsp["jitter_pct"],
        shimmer_db=dsp["shimmer_db"],
        tremor_f0_depth=dsp["tremor_f0_depth"],
        tremor_amp_depth=dsp["tremor_amp_depth"],
        breathiness=dsp["breathiness"],
        formant_warp=dsp["formant_warp"],
        spectral_tilt_db_oct=dsp["spectral_tilt_db_oct"],
        creak_prob=dsp["creak_prob"],
        voice_break_prob=0.0,
        tempo_scale=1.0,
        pause_scale=1.0,
        inhale_prob=0.0,
        chest_warmth=dsp["chest_warmth"],
        hf_cutoff_hz=dsp["hf_cutoff_hz"],
    )
    y = age_voice(audio, sr, params, rng=np.random.default_rng(seed), gender=gender)
    if keep_length:
        y = np.pad(y, (0, max(0, len(audio) - len(y))))[: len(audio)]
    return y.astype(np.float32)


# Alias for backward compatibility
def apply_presbyphonia(
    audio: np.ndarray,
    sr: int,
    params: AcousticAgingParams | None = None,
    age: int = 65,
    gender: str = "nam",
) -> np.ndarray:
    """Backward-compatible entry point, now routed to the v3.0 WORLD engine."""
    return apply_aging_v3(audio, sr=sr, age=age, gender=gender)
