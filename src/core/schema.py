"""Data schemas and type definitions for Elderly Voice Cloning."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RegionEnum(str, Enum):
    MIEN_BAC = "mien_bac"
    MIEN_TRUNG = "mien_trung"
    MIEN_NAM = "mien_nam"


class GenderEnum(str, Enum):
    NAM = "nam"
    NU = "nu"


class CategoryEnum(str, Enum):
    KEU_CUU = "giong_noi_keu_cuu"
    SINH_HOAT = "giong_sinh_hoat"
    CO_NHIEU = "giong_co_nhieu"
    BENCHMARK = "mau_chao_gia_an"


class SpeakerProfile(BaseModel):
    id: str
    name: str
    display_name: str
    gender: GenderEnum
    age: int
    age_bin: str
    region: RegionEnum
    region_display: str
    sub_region: str
    folder_name: str
    base_voice: str
    secondary_voice: Optional[str] = None
    blend_ratio: float = 1.0
    cfg_scale: float = 1.15
    temperature: float = 0.75
    prosody_text: Optional[str] = None
    profile_notes: Optional[str] = None
    # v3.0: multi-voice latent mix ({voice_name: weight}); overrides base/secondary when set
    voice_mix: Optional[dict[str, float]] = None
    # v3.0: per-speaker vocal fingerprint (any field left None is sampled from the age bin)
    voice_traits: Optional["VoiceTraits"] = None

    def resolved_voice_mix(self) -> dict[str, float]:
        """Return normalized {voice: weight}, falling back to legacy base/secondary blend."""
        if self.voice_mix:
            mix = {k: float(v) for k, v in self.voice_mix.items() if v > 0}
        elif self.secondary_voice and self.blend_ratio < 0.99:
            mix = {self.base_voice: self.blend_ratio, self.secondary_voice: 1.0 - self.blend_ratio}
        else:
            mix = {self.base_voice: 1.0}
        total = sum(mix.values()) or 1.0
        return {k: v / total for k, v in mix.items()}


class PromptItem(BaseModel):
    id: str
    code: str
    text: str
    intent: str
    urgency: str = "normal"
    tone: Optional[str] = "calm"
    noise_profile: Optional[str] = None
    snr_db: Optional[float] = None
    description: Optional[str] = None
    # v3.0: optional regional phrasings keyed by region ("mien_bac" | "mien_trung" | "mien_nam")
    dialect_variants: Optional[dict[str, str]] = None


class PromptCategory(BaseModel):
    id: str
    display_name: str
    description: str
    prompts: list[PromptItem]


class AcousticAgingParams(BaseModel):
    """Legacy v2 per-age-bin parameters (kept for backward compatibility)."""

    tempo_scale: float = 0.90
    pitch_shift_semitones: float = -1.0
    tremor_depth: float = 0.02
    tremor_rate_hz: float = 5.0
    jitter_factor: float = 0.02
    shimmer_factor: float = 0.04
    breathiness_gain: float = 0.03
    lowpass_cutoff_hz: float = 7000.0


class VoiceTraits(BaseModel):
    """Per-speaker vocal fingerprint. None = sample deterministically from the age bin."""

    f0_offset_st: Optional[float] = None        # speaker pitch offset vs age-bin target (semitones)
    formant_warp: Optional[float] = None        # <1 lowers formants (longer / laxer vocal tract)
    hoarseness: Optional[float] = None          # 0..1 roughness + breathiness severity
    tremor_severity: Optional[float] = None     # 0..1 scales tremor depth
    tremor_rate_hz: Optional[float] = None      # 4..7 Hz
    speech_rate_factor: Optional[float] = None  # multiplies the age-bin tempo
    pitch_range_scale: Optional[float] = None   # intonation range (>=0.85 keeps Vietnamese tones)
    spectral_tilt_db_oct: Optional[float] = None  # negative = weaker, darker voice


class VoiceAgingParams(BaseModel):
    """Fully resolved DSP parameters for one utterance (WORLD aging engine)."""

    target_f0_hz: float = 0.0                   # 0 = keep source mean F0
    f0_range_scale: float = 1.0
    jitter_pct: float = 0.0                     # added frame-level F0 perturbation (std, %)
    shimmer_db: float = 0.0                     # added frame-level amplitude perturbation (std, dB)
    tremor_rate_hz: float = 5.0
    tremor_f0_depth: float = 0.0                # fractional F0 modulation depth
    tremor_amp_depth: float = 0.0               # fractional amplitude modulation depth
    breathiness: float = 0.0                    # 0..1 aperiodicity raise
    formant_warp: float = 1.0
    spectral_tilt_db_oct: float = 0.0
    creak_prob: float = 0.0                     # vocal fry at phrase ends
    voice_break_prob: float = 0.0               # brief phonation breaks (per second of voicing)
    tempo_scale: float = 1.0                    # <1 = slower speech
    pause_scale: float = 1.0                    # >1 = longer within-utterance pauses
    inhale_prob: float = 0.0                    # audible breath before the utterance
    chest_warmth: float = 0.10                  # low-mid resonance boost
    hf_cutoff_hz: float = 0.0                   # 0 = no high-frequency softening

    def to_dict(self) -> dict[str, float]:
        return {k: round(float(v), 4) for k, v in self.model_dump().items()}


class AudioSampleMetadata(BaseModel):
    sample_id: str
    file_name: str
    relative_path: str
    absolute_path: str
    speaker_id: str
    speaker_name: str
    age: int
    age_bin: str
    gender: str
    region: str
    category: str
    utterance_text: str
    intent: str
    urgency: str
    noise_type: str = "clean"
    snr_db: Optional[float] = None
    duration_sec: float
    sample_rate: int = 48000
    channels: int = 1
    f0_mean_hz: Optional[float] = None
    jitter_pct: Optional[float] = None
    shimmer_pct: Optional[float] = None
    hnr_db: Optional[float] = None
    source: str = "synthetic"
    model_version: str = "zerotts-v3.0-world-aging"
    created_at: str
    # v3.0 additions
    variant_id: int = 0
    seed: Optional[int] = None
    spoken_text: Optional[str] = None
    tone: Optional[str] = None
    voice_mix: Optional[dict[str, float]] = None
    dsp_params: Optional[dict[str, Any]] = None
    f0_std_hz: Optional[float] = None
    cpps_db: Optional[float] = None
    speech_rate_syl_s: Optional[float] = None
    pause_ratio: Optional[float] = None
    cer: Optional[float] = None
    asr_text: Optional[str] = None
    speaker_sim_to_centroid: Optional[float] = None
    qc_pass: Optional[bool] = None
    qc_reasons: Optional[list[str]] = None
    attempts: int = 1


SpeakerProfile.model_rebuild()
