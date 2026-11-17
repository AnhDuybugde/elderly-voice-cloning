"""Configuration loader for speakers, prompts, and acoustic parameters."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml

from src.core.schema import (
    SpeakerProfile,
    PromptCategory,
    AcousticAgingParams,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DATASET_DIR = DATA_DIR / "elderly_dataset"


def load_yaml(file_path: Path | str) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_speakers_config(path: Path | str | None = None) -> list[SpeakerProfile]:
    target = Path(path) if path else CONFIGS_DIR / "speakers.yaml"
    raw = load_yaml(target)
    return [SpeakerProfile(**item) for item in raw.get("speakers", [])]


def get_prompts_config(path: Path | str | None = None) -> list[PromptCategory]:
    target = Path(path) if path else CONFIGS_DIR / "prompts.yaml"
    raw = load_yaml(target)
    return [PromptCategory(**cat) for cat in raw.get("categories", [])]


def get_aging_params_for_age(age_bin: str, path: Path | str | None = None) -> AcousticAgingParams:
    target = Path(path) if path else CONFIGS_DIR / "acoustic_profiles.yaml"
    raw = load_yaml(target)
    groups = raw.get("age_groups", {})
    if age_bin in groups:
        data = dict(groups[age_bin])
        data.pop("description", None)
        return AcousticAgingParams(**data)
    # Default to 60_69 if unspecified
    default_data = dict(groups.get("60_69", {}))
    default_data.pop("description", None)
    return AcousticAgingParams(**default_data)
