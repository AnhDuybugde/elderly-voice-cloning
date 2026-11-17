import numpy as np

from src.metrics.acoustic_features import analyze_audio_sample, count_vi_syllables, speech_activity
from src.metrics.intelligibility import cer, normalize_vi, wer

SR = 48000


def _pulse_voice(f0=120.0, dur=1.5, period_jitter=0.0, seed=0):
    """Glottal-pulse-like source: one decaying resonance per cycle, optional period jitter."""
    rng = np.random.default_rng(seed)
    y = np.zeros(int(dur * SR))
    t = 0.0
    n_ring = int(0.006 * SR)
    ring = np.exp(-np.arange(n_ring) / (0.0012 * SR)) * np.sin(2 * np.pi * 700 * np.arange(n_ring) / SR)
    while t < dur - 0.01:
        i = int(t * SR)
        seg = y[i : i + n_ring]
        seg += ring[: len(seg)]
        t += (1.0 / f0) * (1.0 + period_jitter * rng.standard_normal())
    return (0.5 * y / np.max(np.abs(y))).astype(np.float32)


def test_jitter_is_low_for_periodic_and_rises_with_period_noise():
    clean = analyze_audio_sample(_pulse_voice(period_jitter=0.0), SR, gender="nam")
    noisy = analyze_audio_sample(_pulse_voice(period_jitter=0.03), SR, gender="nam")
    assert 110 < clean["f0_mean_hz"] < 130
    assert clean["jitter_pct"] < 0.5
    assert noisy["jitter_pct"] > 1.5
    assert noisy["jitter_pct"] > clean["jitter_pct"] * 3
    assert clean["hnr_db"] > noisy["hnr_db"]


def test_silence_returns_zeros_not_errors():
    m = analyze_audio_sample(np.zeros(SR, dtype=np.float32), SR)
    assert m["f0_mean_hz"] == 0.0 and m["jitter_pct"] == 0.0


def test_speech_activity_detects_interior_pause():
    tone = _pulse_voice(dur=0.5)
    y = np.concatenate([np.zeros(SR // 10), tone, np.zeros(SR // 2), tone, np.zeros(SR // 10)])
    act = speech_activity(y, SR)
    assert act["n_pauses"] == 1
    assert 0.25 < act["pause_ratio"] < 0.45
    assert 400 < act["mean_pause_ms"] < 600


def test_syllable_count_and_speech_rate():
    assert count_vi_syllables("Gia An ơi, cứu tôi với!") == 6
    y = np.concatenate([_pulse_voice(dur=2.0), np.zeros(SR // 5)])
    m = analyze_audio_sample(y, SR, gender="nam", text="một hai ba bốn năm sáu bảy tám")
    assert 3.0 < m["speech_rate_syl_s"] < 5.0


def test_cer_wer_vietnamese_normalization():
    assert normalize_vi("Gia An ơi, CỨU tôi!") == "gia an ơi cứu tôi"
    assert cer("Gia An ơi, cứu tôi với!", "gia an ơi cứu tôi với") == 0.0
    assert cer("cứu tôi", "cứu bà") > 0.0
    # Filler words added by the humanizer do not count as errors
    assert wer("Gia An ơi, cứu tôi", "Gia An ơi ờ cứu tôi") == 0.0
    # ASR "standardizes" dialect words and writes digits: not a speech error
    assert cer("Tối nay tám giờ nhắc tui uống thuốc nghen", "Tối nay 8h nhắc tôi uống thuốc nghe") == 0.0
    assert wer("Có ai ở ngoài đó hông?", "Có ai ở ngoài đó không?") == 0.0
    assert cer("cứu tui", "cứu tui", drop_fillers=True) == 0.0
