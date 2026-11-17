"""Acoustic noise generator and mixer for noisy realistic scenarios."""

from __future__ import annotations

import numpy as np
import scipy.signal as signal


def generate_pink_noise(n_samples: int) -> np.ndarray:
    """Generate 1/f pink noise using Voss-McCartney algorithm approximation."""
    white = np.random.normal(0, 1.0, size=n_samples)
    # Pink filter via IIR approximation
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1.0, -2.494956002, 2.017265875, -0.522189400]
    pink = signal.lfilter(b, a, white)
    return pink.astype(np.float32)


def generate_fan_noise(n_samples: int, sr: int) -> np.ndarray:
    """Simulate electric fan or air conditioning hum (low rumble + motor tonal hum)."""
    t = np.arange(n_samples) / sr
    # 50 Hz or 60 Hz hum + harmonics
    hum = (
        0.4 * np.sin(2 * np.pi * 50 * t)
        + 0.2 * np.sin(2 * np.pi * 100 * t)
        + 0.1 * np.sin(2 * np.pi * 150 * t)
    )
    # Pink air airflow noise
    air = generate_pink_noise(n_samples)
    b_lp, a_lp = signal.butter(3, min(800.0 / (sr / 2), 0.95), btype="low")
    filtered_air = signal.lfilter(b_lp, a_lp, air)

    combined = hum + 1.2 * filtered_air
    return (combined / (np.max(np.abs(combined)) + 1e-8)).astype(np.float32)


def generate_kitchen_noise(n_samples: int, sr: int) -> np.ndarray:
    """Simulate kitchen background: clattering dishes, running water, boiling."""
    base_noise = generate_pink_noise(n_samples)
    b_bp, a_bp = signal.butter(2, [min(400.0 / (sr / 2), 0.8), min(3500.0 / (sr / 2), 0.95)], btype="band")
    water_flow = signal.lfilter(b_bp, a_bp, base_noise) * 0.5

    # Random clangs (metallic / ceramic impulses)
    clangs = np.zeros(n_samples, dtype=np.float32)
    # About 3-6 clangs per second
    n_clangs = max(2, int((n_samples / sr) * 4))
    clang_indices = np.random.choice(n_samples - int(0.2 * sr), size=n_clangs, replace=False)

    for idx in clang_indices:
        clang_len = int(0.15 * sr)
        t_clang = np.arange(clang_len) / sr
        freq1 = np.random.uniform(1800, 3200)
        freq2 = np.random.uniform(3500, 5000)
        decay = np.exp(-t_clang * np.random.uniform(25, 45))
        clang_sound = (np.sin(2 * np.pi * freq1 * t_clang) + 0.5 * np.sin(2 * np.pi * freq2 * t_clang)) * decay
        clangs[idx : idx + clang_len] += (clang_sound * np.random.uniform(0.6, 1.2)).astype(np.float32)

    combined = water_flow + clangs
    return (combined / (np.max(np.abs(combined)) + 1e-8)).astype(np.float32)


def generate_tv_background(n_samples: int, sr: int) -> np.ndarray:
    """Simulate muffled TV news broadcast / speech in background."""
    white = np.random.normal(0, 1.0, size=n_samples)
    # Formant-like filtering for speech-like babble
    b1, a1 = signal.butter(2, [min(300.0 / (sr / 2), 0.8), min(2800.0 / (sr / 2), 0.95)], btype="band")
    speech_band = signal.lfilter(b1, a1, white)

    # Low frequency modulation (speech cadence ~3-5 Hz)
    t = np.arange(n_samples) / sr
    mod = 0.5 * (1.0 + np.sin(2 * np.pi * 3.5 * t) * np.sin(2 * np.pi * 1.8 * t))
    tv_sound = speech_band * mod

    # Add subtle TV hum
    hum = 0.15 * np.sin(2 * np.pi * 100 * t)
    combined = tv_sound + hum
    return (combined / (np.max(np.abs(combined)) + 1e-8)).astype(np.float32)


def generate_street_ambient(n_samples: int, sr: int) -> np.ndarray:
    """Simulate traffic rumble from street outside house."""
    pink = generate_pink_noise(n_samples)
    # Low frequency rumble < 600 Hz
    b, a = signal.butter(3, min(600.0 / (sr / 2), 0.95), btype="low")
    rumble = signal.lfilter(b, a, pink)

    # Occasional car pass / horn
    t = np.arange(n_samples) / sr
    horn_freq = 440.0
    horn = 0.15 * np.sin(2 * np.pi * horn_freq * t) * np.exp(-((t - (n_samples / sr) * 0.5) ** 2) / 0.1)

    combined = rumble + horn
    return (combined / (np.max(np.abs(combined)) + 1e-8)).astype(np.float32)


def apply_room_reverb(audio: np.ndarray, sr: int) -> np.ndarray:
    """Simulate indoor room acoustic reflections (far-field acoustics)."""
    # Simple comb/all-pass Schroeder reverberator approximation
    delay_ms = [29, 37, 44, 53]
    gains = [0.45, 0.35, 0.28, 0.20]

    reverb = np.zeros_like(audio)
    for d_ms, g in zip(delay_ms, gains):
        d_samples = int((d_ms / 1000.0) * sr)
        if d_samples < len(audio):
            delayed = np.pad(audio[:-d_samples], (d_samples, 0), mode="constant")
            reverb += delayed * g

    wet = audio * 0.65 + reverb * 0.35
    max_val = np.max(np.abs(wet))
    if max_val > 0:
        wet = wet / max_val
    return wet.astype(np.float32)


def mix_audio_with_noise(
    clean_audio: np.ndarray,
    noise_profile: str,
    snr_db: float,
    sr: int = 24000,
) -> np.ndarray:
    """Mix clean speech with environmental noise at specified SNR (dB).

    Args:
        clean_audio: Clean audio signal array.
        noise_profile: Profile name ('tv_background', 'kitchen_noise', etc.).
        snr_db: Desired Signal-to-Noise Ratio in dB.
        sr: Sample rate in Hz.

    Returns:
        Mixed audio array normalized to safe headroom.
    """
    n_samples = len(clean_audio)
    if n_samples == 0:
        return clean_audio

    # Handle farfield reverb first if requested
    signal_to_mix = clean_audio
    if noise_profile == "room_reverb_farfield":
        signal_to_mix = apply_room_reverb(clean_audio, sr)
        noise = generate_fan_noise(n_samples, sr)
    elif noise_profile == "tv_background":
        noise = generate_tv_background(n_samples, sr)
    elif noise_profile == "kitchen_noise":
        noise = generate_kitchen_noise(n_samples, sr)
    elif noise_profile == "fan_noise":
        noise = generate_fan_noise(n_samples, sr)
    elif noise_profile == "street_ambient":
        noise = generate_street_ambient(n_samples, sr)
    else:
        # Default pink noise
        noise = generate_pink_noise(n_samples)

    # Compute signal power and required noise power
    p_signal = np.mean(signal_to_mix**2) + 1e-10
    target_p_noise = p_signal / (10.0 ** (snr_db / 10.0))
    current_p_noise = np.mean(noise**2) + 1e-10

    scale = np.sqrt(target_p_noise / current_p_noise)
    scaled_noise = noise * scale

    mixed = signal_to_mix + scaled_noise

    # Normalize to avoid clipping
    peak = np.max(np.abs(mixed))
    if peak > 0:
        mixed = (mixed / peak) * 0.85

    return mixed.astype(np.float32)
