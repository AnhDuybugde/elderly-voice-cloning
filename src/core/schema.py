"""Data schemas and type definitions for Elderly Voice Cloning."""

from __future__ import annotations

from enum import Enum
from typing import Optional
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


class PromptCategory(BaseModel):
    id: str
    display_name: str
    description: str
    prompts: list[PromptItem]


class AcousticAgingParams(BaseModel):
    tempo_scale: float = 0.90
    pitch_shift_semitones: float = -1.0
    tremor_depth: float = 0.02
    tremor_rate_hz: float = 5.0
    jitter_factor: float = 0.02
    shimmer_factor: float = 0.04
    breathiness_gain: float = 0.03
    lowpass_cutoff_hz: float = 7000.0


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
    model_version: str = "zerotts-v2.0-neural-latent-blending"
    created_at: str
