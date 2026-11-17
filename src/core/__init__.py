"""Core module: schema and config."""
from src.core.schema import (
    RegionEnum,
    GenderEnum,
    CategoryEnum,
    SpeakerProfile,
    PromptItem,
    PromptCategory,
    AcousticAgingParams,
    AudioSampleMetadata,
)
from src.core.config import (
    PROJECT_ROOT,
    CONFIGS_DIR,
    DATA_DIR,
    OUTPUT_DATASET_DIR,
    get_speakers_config,
    get_prompts_config,
    get_aging_params_for_age,
)

__all__ = [
    "RegionEnum",
    "GenderEnum",
    "CategoryEnum",
    "SpeakerProfile",
    "PromptItem",
    "PromptCategory",
    "AcousticAgingParams",
    "AudioSampleMetadata",
    "PROJECT_ROOT",
    "CONFIGS_DIR",
    "DATA_DIR",
    "OUTPUT_DATASET_DIR",
    "get_speakers_config",
    "get_prompts_config",
    "get_aging_params_for_age",
]
