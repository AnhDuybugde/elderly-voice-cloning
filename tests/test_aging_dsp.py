import numpy as np
import pytest
from src.core.schema import AcousticAgingParams
from src.synthesis.aging_dsp import apply_presbyphonia
from src.metrics.acoustic_features import analyze_audio_sample


def test_aging_dsp_preserves_audio_quality():
    sr = 24000
    duration = 1.5
    t = np.arange(int(duration * sr)) / sr
    # 130 Hz fundamental tone
    clean = 0.5 * np.sin(2 * np.pi * 130 * t).astype(np.float32)

    params = AcousticAgingParams(
        tempo_scale=0.85,
        pitch_shift_semitones=-1.0,
        tremor_depth=0.03,
        tremor_rate_hz=5.0,
        jitter_factor=0.02,
        shimmer_factor=0.04,
        breathiness_gain=0.02,
        lowpass_cutoff_hz=6500.0,
    )

    aged = apply_presbyphonia(clean, sr=sr, params=params)

    assert len(aged) > 0
    # Because tempo_scale < 1.0, duration should be stretched
    assert len(aged) > len(clean)

    # Check maximum amplitude does not clip
    max_peak = np.max(np.abs(aged))
    assert max_peak <= 0.95

    # Check acoustic analysis runs without error
    metrics = analyze_audio_sample(aged, sr)
    assert metrics["duration_sec"] > 0
    assert metrics["f0_mean_hz"] > 0
