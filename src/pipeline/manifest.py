"""Manifest and metadata export utilities (JSONL and CSV with UTF-8 BOM)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from src.core.schema import AudioSampleMetadata


def export_manifest_jsonl(metadata_list: Sequence[AudioSampleMetadata], output_path: Path | str) -> None:
    """Export metadata to a JSONL file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in metadata_list:
            f.write(json.dumps(item.model_dump(), ensure_ascii=False) + "\n")


def export_manifest_csv(metadata_list: Sequence[AudioSampleMetadata], output_path: Path | str) -> None:
    """Export metadata to CSV (using UTF-8 with BOM for cross-platform Excel compatibility)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not metadata_list:
        return

    fields = list(metadata_list[0].model_dump().keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in metadata_list:
            row = item.model_dump()
            # Nested fields (dsp_params, voice_mix, qc_reasons) are stored as JSON strings
            for k, v in row.items():
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v, ensure_ascii=False)
            writer.writerow(row)


def generate_summary_report(metadata_list: Sequence[AudioSampleMetadata]) -> dict[str, any]:
    """Calculate aggregate dataset statistics."""
    total_samples = len(metadata_list)
    total_duration = sum(item.duration_sec for item in metadata_list)

    by_speaker = {}
    by_category = {}
    by_region = {}
    by_age_bin = {}

    for item in metadata_list:
        by_speaker[item.speaker_name] = by_speaker.get(item.speaker_name, 0) + 1
        by_category[item.category] = by_category.get(item.category, 0) + 1
        by_region[item.region] = by_region.get(item.region, 0) + 1
        by_age_bin[item.age_bin] = by_age_bin.get(item.age_bin, 0) + 1

    qc_known = [m for m in metadata_list if getattr(m, "qc_pass", None) is not None]
    qc_pass_rate = (sum(1 for m in qc_known if m.qc_pass) / len(qc_known)) if qc_known else None

    return {
        "qc_pass_rate": round(qc_pass_rate, 4) if qc_pass_rate is not None else None,
        "total_samples": total_samples,
        "total_duration_sec": round(total_duration, 2),
        "total_duration_min": round(total_duration / 60.0, 2),
        "speakers_count": len(by_speaker),
        "by_speaker": by_speaker,
        "by_category": by_category,
        "by_region": by_region,
        "by_age_bin": by_age_bin,
    }
