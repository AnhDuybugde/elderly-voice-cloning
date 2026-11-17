"""Acoustic aging processor (Presbyphonia DSP).

Simulates biological and physiological vocal tract aging in elderly individuals:
- Vocal fold tremor (neuromuscular oscillation ~4-7 Hz)
- Jitter (period perturbation)
- Shimmer (amplitude perturbation)
- Glottal breathiness / aspirate noise
- Pitch shifting & Formant relaxation
- Speech rate slowing & pause extension
- High-frequency harmonic rolloff
"""

from __future__ import annotations

import numpy as np
import scipy.signal as signal
import librosa

from src.core.schema import AcousticAgingParams


def apply_presbyphonia(
    audio: np.ndarray,
    sr: int,
    params: AcousticAgingParams,
) -> np.ndarray:
    """Apply comprehensive physiological aging transformations to a speech signal.

    Args:
        audio: 1D float32 numpy array, normalized in range [-1.0, 1.0].
        sr: Sample rate in Hz.
        params: Acoustic aging configuration parameters.

    Returns:
        Processed 1D float32 numpy array.
    """
    if len(audio) == 0:
        return audio

    y = audio.astype(np.float32).copy()

    # 1. Pitch shift (slight downward or sex-specific adjustment)
    if abs(params.pitch_shift_semitones) > 0.05:
        # librosa pitch_shift preserves length
        y = librosa.effects.pitch_shift(
            y,
            sr=sr,
            n_steps=params.pitch_shift_semitones,
            bins_per_octave=12,
        )

    # 2. Time-stretch / Slower tempo (elderly articulation rate is 10-25% slower)
    if params.tempo_scale > 0 and abs(params.tempo_scale - 1.0) > 0.02:
        # rate < 1.0 slows down audio (lengthens duration)
        y = librosa.effects.time_stretch(y, rate=params.tempo_scale)

    n_samples = len(y)
    t = np.arange(n_samples) / sr

    # 3. Senile Vocal Tremor (neuromuscular tremor: 4.5 - 6.5 Hz modulation)
    if params.tremor_depth > 0:
        # Amplitude tremor modulation
        tremor_envelope = 1.0 + params.tremor_depth * np.sin(
            2 * np.pi * params.tremor_rate_hz * t
        )
        y = y * tremor_envelope.astype(np.float32)

    # 4. Shimmer simulation (short-term cycle-to-cycle amplitude perturbation)
    if params.shimmer_factor > 0:
        # Create pink-ish low frequency amplitude jitter
        shimmer_noise = np.random.normal(0, params.shimmer_factor, size=n_samples)
        # Lowpass filter the shimmer noise so it fluctuates at ~10-30 Hz
        b_shimmer, a_shimmer = signal.butter(2, 30.0 / (sr / 2), btype="low")
        filtered_shimmer = signal.lfilter(b_shimmer, a_shimmer, shimmer_noise)
        y = y * (1.0 + filtered_shimmer.astype(np.float32))

    # 5. Breathiness (glottal leakage / aspirate noise in mid-high frequencies)
    if params.breathiness_gain > 0:
        # Generate white noise
        raw_noise = np.random.normal(0, 1.0, size=n_samples).astype(np.float32)
        # Bandpass filter between 1500 Hz and 4500 Hz (characteristic breathy band)
        nyquist = sr / 2.0
        low_cut = min(1500.0 / nyquist, 0.9)
        high_cut = min(4500.0 / nyquist, 0.95)
        if low_cut < high_cut:
            b_band, a_band = signal.butter(3, [low_cut, high_cut], btype="band")
            breath_band = signal.lfilter(b_band, a_band, raw_noise)

            # Modulate breathiness with envelope of the original speech signal
            # (breathiness mostly occurs during phonation and at trailing phrase ends)
            envelope = np.abs(signal.hilbert(y))
            # Smooth the envelope
            b_env, a_env = signal.butter(2, 20.0 / nyquist, btype="low")
            smooth_env = signal.lfilter(b_env, a_env, envelope)
            smooth_env = np.clip(smooth_env, 0, None)
            smooth_env = smooth_env / (np.max(smooth_env) + 1e-8)

            y = y + (params.breathiness_gain * breath_band * smooth_env).astype(np.float32)

    # 6. Lowpass filtering (natural high frequency harmonic rolloff with age)
    if params.lowpass_cutoff_hz < (sr / 2):
        norm_cutoff = min(params.lowpass_cutoff_hz / (sr / 2), 0.98)
        b_lp, a_lp = signal.butter(4, norm_cutoff, btype="low")
        y = signal.lfilter(b_lp, a_lp, y).astype(np.float32)

    # 7. Normalize amplitude to prevent clipping and ensure consistent headroom (-1.5 dB)
    max_val = np.max(np.abs(y))
    if max_val > 1e-6:
        target_peak = 0.85  # ~ -1.4 dBFS
        y = (y / max_val) * target_peak

    return y.astype(np.float32)
