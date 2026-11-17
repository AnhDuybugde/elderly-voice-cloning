"""Resolve per-utterance aging parameters from speaker profile + age bin + tone.

Layers (later layers modify earlier ones):
    1. age-bin DSP base           (configs/acoustic_profiles.yaml: profiles.<gender>.<bin>.dsp)
    2. calibrated overrides        (profiles written by tools/calibrate_aging.py)
    3. speaker vocal fingerprint   (VoiceTraits: explicit in speakers.yaml or sampled with a
                                    seed derived from speaker.id -> stable identity)
    4. tone modifier               (panicked / in_pain / breathless / calm ...)
    5. per-variant micro jitter    (small tempo / pause / F0 changes between takes)
    6. adaptive targets            (target F0 and tempo computed from the measured source)
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Optional

import numpy as np

from src.core.config import CONFIGS_DIR, load_yaml
from src.core.schema import SpeakerProfile, VoiceAgingParams, VoiceTraits

TEMPO_LIMITS = (0.55, 1.15)


def stable_seed(*parts) -> int:
    """Deterministic 32-bit seed from arbitrary parts (stable across processes)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


@lru_cache(maxsize=4)
def _load_profiles(path: Optional[str] = None) -> dict:
    return load_yaml(path or CONFIGS_DIR / "acoustic_profiles.yaml")


def clear_profile_cache() -> None:
    _load_profiles.cache_clear()


def age_bin_for(age: int) -> str:
    if age < 60:
        return "50_59"
    if age < 70:
        return "60_69"
    if age < 80:
        return "70_79"
    return "80_plus"


def get_profile(gender: str, age_bin: str, path: Optional[str] = None) -> dict:
    cfg = _load_profiles(path)
    prof = cfg["profiles"][gender][age_bin]
    calibrated = (cfg.get("calibrated") or {}).get(gender, {}).get(age_bin, {})
    dsp = dict(prof["dsp"])
    dsp.update(calibrated)
    return {"target": prof["target"], "qc": prof["qc"], "dsp": dsp, "traits": prof["traits"]}


def get_tone_modifier(tone: Optional[str], path: Optional[str] = None) -> dict:
    cfg = _load_profiles(path)
    return dict((cfg.get("tone_modifiers") or {}).get(tone or "calm", {}) or {})


def resolve_traits(speaker: SpeakerProfile, path: Optional[str] = None) -> VoiceTraits:
    """Explicit traits from speakers.yaml win; missing ones are sampled deterministically."""
    gender = speaker.gender.value if hasattr(speaker.gender, "value") else str(speaker.gender)
    ranges = get_profile(gender, speaker.age_bin, path)["traits"]
    rng = np.random.default_rng(stable_seed("traits", speaker.id))
    explicit = speaker.voice_traits.model_dump() if speaker.voice_traits else {}

    values = {}
    for name in VoiceTraits.model_fields:
        lo, hi = ranges.get(name, (0.0, 0.0))
        sampled = float(rng.uniform(lo, hi))  # always draw -> stable stream regardless of overrides
        values[name] = explicit.get(name) if explicit.get(name) is not None else sampled
    # formant_warp in the ranges table is an offset around the bin base
    if explicit.get("formant_warp") is None:
        values["formant_warp"] = 1.0 + values["formant_warp"]
    return VoiceTraits(**values)


def resolve_aging_params(
    speaker: SpeakerProfile,
    tone: Optional[str] = None,
    variant_rng: Optional[np.random.Generator] = None,
    source_rate_syl_s: Optional[float] = None,
    path: Optional[str] = None,
) -> VoiceAgingParams:
    gender = speaker.gender.value if hasattr(speaker.gender, "value") else str(speaker.gender)
    prof = get_profile(gender, speaker.age_bin, path)
    dsp = prof["dsp"]
    target = prof["target"]
    traits = resolve_traits(speaker, path)
    mod = get_tone_modifier(tone, path)
    rng = variant_rng if variant_rng is not None else np.random.default_rng(0)

    h = float(traits.hoarseness)
    s = float(traits.tremor_severity)

    # Per-take micro variation (a real person never says a sentence the same way twice)
    take_f0 = rng.normal(0.0, 0.25)
    take_tempo = rng.normal(1.0, 0.03)
    take_pause = rng.normal(1.0, 0.08)

    f0_st = traits.f0_offset_st + mod.get("f0_offset_st", 0.0) + take_f0
    target_f0 = float(target["f0_hz"]) * 2 ** (f0_st / 12.0)

    target_rate = float(target["speech_rate_syl_s"]) * traits.speech_rate_factor * mod.get("tempo_mul", 1.0) * take_tempo
    if source_rate_syl_s and source_rate_syl_s > 0:
        tempo = target_rate / source_rate_syl_s
    else:
        tempo = target_rate / 4.5  # typical ZeroTTS reading rate
    tempo = float(np.clip(tempo, *TEMPO_LIMITS))

    breath = dsp["breathiness"] * (0.6 + 0.8 * h) + mod.get("breathiness_add", 0.0)

    return VoiceAgingParams(
        target_f0_hz=target_f0,
        f0_range_scale=float(np.clip(traits.pitch_range_scale * mod.get("range_mul", 1.0), 0.85, 1.25)),
        jitter_pct=dsp["jitter_pct"] * (0.5 + h),
        shimmer_db=dsp["shimmer_db"] * (0.5 + h),
        tremor_rate_hz=traits.tremor_rate_hz,
        tremor_f0_depth=dsp["tremor_f0_depth"] * (0.4 + 1.2 * s),
        tremor_amp_depth=dsp["tremor_amp_depth"] * (0.4 + 1.2 * s),
        breathiness=float(np.clip(breath, 0.0, 0.85)),
        formant_warp=dsp["formant_warp"] * traits.formant_warp,
        spectral_tilt_db_oct=dsp["spectral_tilt_db_oct"] + traits.spectral_tilt_db_oct,
        creak_prob=float(np.clip(dsp["creak_prob"] * (0.5 + h) + mod.get("creak_add", 0.0), 0.0, 0.9)),
        voice_break_prob=dsp["voice_break_prob"] * (0.5 + h),
        tempo_scale=tempo,
        pause_scale=float(np.clip(dsp["pause_scale"] * mod.get("pause_mul", 1.0) * take_pause, 0.6, 2.5)),
        inhale_prob=float(mod.get("inhale_prob", dsp["inhale_prob"])),
        chest_warmth=dsp["chest_warmth"],
        hf_cutoff_hz=dsp["hf_cutoff_hz"],
    )
