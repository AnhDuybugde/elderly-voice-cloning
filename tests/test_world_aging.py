import numpy as np
import pyworld as pw
import pytest

from src.core.schema import GenderEnum, RegionEnum, SpeakerProfile, VoiceAgingParams
from src.metrics.acoustic_features import analyze_audio_sample
from src.synthesis.aging_dsp import apply_aging_v3
from src.synthesis.voice_profile import get_profile, resolve_aging_params, resolve_traits
from src.synthesis.world_aging import age_voice

SR = 48000


def _voice(f0=120.0, dur=2.0, contour=0.08, seed=0):
    """Harmonic voice with a tone-like F0 contour and a formant-ish spectral envelope."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    f0_t = f0 * (1.0 + contour * np.sin(2 * np.pi * 1.3 * t))
    phase = 2 * np.pi * np.cumsum(f0_t) / SR
    y = np.zeros_like(t)
    for k in range(1, 40):
        fk = k * f0
        gain = np.exp(-((fk - 600) ** 2) / (2 * 250**2)) + 0.6 * np.exp(-((fk - 1500) ** 2) / (2 * 300**2)) + 0.05
        y += gain / k**0.5 * np.sin(k * phase)
    y += 0.002 * rng.standard_normal(len(t))
    return (0.6 * y / np.max(np.abs(y))).astype(np.float32)


def _mean_metrics(audio_fn, n_seeds=2, gender="nam"):
    ms = [analyze_audio_sample(audio_fn(s), SR, gender=gender) for s in range(n_seeds)]
    return {k: float(np.mean([m[k] for m in ms])) for k in ("jitter_pct", "shimmer_pct", "hnr_db", "cpps_db")}


def test_aging_cues_increase_with_age():
    src = _voice()
    by_age = {
        age: _mean_metrics(lambda s, a=age: apply_aging_v3(src, SR, age=a, gender="nam", seed=s))
        for age in (55, 65, 75, 85)
    }
    assert by_age[85]["jitter_pct"] > by_age[65]["jitter_pct"] > by_age[55]["jitter_pct"]
    assert by_age[85]["shimmer_pct"] > by_age[55]["shimmer_pct"]
    assert by_age[85]["hnr_db"] < by_age[55]["hnr_db"]
    assert by_age[85]["cpps_db"] < by_age[55]["cpps_db"]


def test_target_f0_is_reached():
    src = _voice(f0=230.0, contour=0.03)
    out = age_voice(src, SR, VoiceAgingParams(target_f0_hz=175.0), np.random.default_rng(0), gender="nu")
    f0 = analyze_audio_sample(out, SR, gender="nu")["f0_mean_hz"]
    assert abs(f0 - 175.0) / 175.0 < 0.10


def test_tone_contour_is_preserved():
    """Vietnamese tones live in the F0 contour: aging may shift/scale it but not destroy it."""
    src = _voice(f0=120.0, contour=0.10)
    params = VoiceAgingParams(target_f0_hz=110.0, f0_range_scale=0.9, jitter_pct=1.5, tremor_f0_depth=0.015,
                              tremor_amp_depth=0.05, breathiness=0.2)
    out = age_voice(src, SR, params, np.random.default_rng(1), gender="nam")

    def contour(x):
        f0, _ = pw.harvest(x.astype(np.float64), SR, f0_floor=60, f0_ceil=300, frame_period=5)
        return f0

    a, b = contour(src), contour(out)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    both = (a > 0) & (b > 0)
    # Smooth away jitter/tremor so we compare the slow (tonal) contour only
    k = np.hanning(41) / np.hanning(41).sum()
    la = np.convolve(np.log(np.where(both, a, 1)), k, mode="same")[both]
    lb = np.convolve(np.log(np.where(both, b, 1)), k, mode="same")[both]
    assert np.corrcoef(la, lb)[0, 1] > 0.9


def test_deterministic_with_seed_and_safe_levels():
    src = _voice()
    p = VoiceAgingParams(jitter_pct=2.0, shimmer_db=0.3, tremor_f0_depth=0.02, tremor_amp_depth=0.08,
                         breathiness=0.4, creak_prob=0.5, voice_break_prob=0.5, inhale_prob=1.0,
                         tempo_scale=0.8, pause_scale=1.5)
    a = age_voice(src, SR, p, np.random.default_rng(7), gender="nam")
    b = age_voice(src, SR, p, np.random.default_rng(7), gender="nam")
    c = age_voice(src, SR, p, np.random.default_rng(8), gender="nam")
    assert np.array_equal(a, b)
    assert not np.array_equal(a[: len(c)], c[: len(a)])
    assert not np.isnan(a).any()
    assert np.max(np.abs(a)) <= 0.90  # <= -1 dBFS headroom


def test_tempo_scale_slows_speech():
    src = _voice(dur=2.0)
    out = age_voice(src, SR, VoiceAgingParams(tempo_scale=0.7), np.random.default_rng(0), gender="nam")
    assert len(out) / len(src) == pytest.approx(1 / 0.7, rel=0.08)


def _speaker(spk_id, age, age_bin, gender=GenderEnum.NAM, **kw):
    return SpeakerProfile(
        id=spk_id, name="Ong_Test", display_name="Ông Test", gender=gender, age=age, age_bin=age_bin,
        region=RegionEnum.MIEN_BAC, region_display="Bắc", sub_region="ha_noi",
        folder_name=f"Ong_Test_{age}_tuoi_Mien_Bac", base_voice="huuduc", **kw,
    )


def test_speaker_fingerprint_is_stable_and_distinct():
    a1 = resolve_traits(_speaker("spk_a", 72, "70_79"))
    a2 = resolve_traits(_speaker("spk_a", 72, "70_79"))
    b = resolve_traits(_speaker("spk_b", 72, "70_79"))
    assert a1 == a2
    assert a1 != b
    ranges = get_profile("nam", "70_79")["traits"]
    lo, hi = ranges["hoarseness"]
    assert lo <= a1.hoarseness <= hi


def test_explicit_traits_override_sampling():
    spk = _speaker("spk_c", 82, "80_plus", voice_traits={"hoarseness": 0.95, "formant_warp": 0.97})
    traits = resolve_traits(spk)
    assert traits.hoarseness == 0.95 and traits.formant_warp == 0.97


def test_tone_modifier_and_age_bin_effects():
    young = _speaker("spk_d", 52, "50_59")
    old = _speaker("spk_d", 85, "80_plus")
    rng = lambda: np.random.default_rng(0)  # noqa: E731
    calm = resolve_aging_params(old, "calm", rng(), source_rate_syl_s=4.5)
    panic = resolve_aging_params(old, "panicked", rng(), source_rate_syl_s=4.5)
    y = resolve_aging_params(young, "calm", rng(), source_rate_syl_s=4.5)
    assert panic.target_f0_hz > calm.target_f0_hz
    assert panic.tempo_scale > calm.tempo_scale
    assert calm.tempo_scale < y.tempo_scale
    assert calm.jitter_pct > y.jitter_pct and calm.breathiness > y.breathiness
