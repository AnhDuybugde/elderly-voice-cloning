import numpy as np
import pytest
from src.synthesis.aging_dsp import apply_analog_warmth_and_aging
from src.metrics.acoustic_features import analyze_audio_sample


def test_aging_dsp_preserves_audio_quality():
    sr = 48000
    duration = 1.5
    t = np.arange(int(duration * sr)) / sr
    # 130 Hz fundamental tone
    clean = 0.5 * np.sin(2 * np.pi * 130 * t).astype(np.float32)

    enhanced = apply_analog_warmth_and_aging(clean, sr=sr, age=75)

    assert len(enhanced) == len(clean)

    # Check maximum amplitude does not clip
    max_peak = np.max(np.abs(enhanced))
    assert max_peak <= 0.90

    # Check acoustic analysis runs without error
    metrics = analyze_audio_sample(enhanced, sr)
    assert metrics["duration_sec"] > 0
    assert metrics["f0_mean_hz"] > 0
