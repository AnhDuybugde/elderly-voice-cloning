import numpy as np
import pytest
from src.noise.augment import (
    generate_fan_noise,
    generate_kitchen_noise,
    generate_tv_background,
    mix_audio_with_noise,
    apply_room_reverb,
)


def test_noise_generators():
    sr = 24000
    n = 24000

    fan = generate_fan_noise(n, sr)
    assert len(fan) == n
    assert not np.isnan(fan).any()

    kitchen = generate_kitchen_noise(n, sr)
    assert len(kitchen) == n
    assert not np.isnan(kitchen).any()

    tv = generate_tv_background(n, sr)
    assert len(tv) == n
    assert not np.isnan(tv).any()


def test_mix_audio_with_noise():
    sr = 24000
    n = 24000
    t = np.arange(n) / sr
    clean = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

    mixed = mix_audio_with_noise(clean, noise_profile="tv_background", snr_db=10.0, sr=sr)
    assert len(mixed) == n
    assert not np.isnan(mixed).any()
    assert np.max(np.abs(mixed)) <= 0.95
