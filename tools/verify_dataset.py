#!/usr/bin/env python3
"""Dataset verification tool: checks audio files, directory layout, and manifest consistency."""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
import soundfile as sf
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import OUTPUT_DATASET_DIR


def verify_dataset(dataset_dir: Path | str) -> bool:
    target_dir = Path(dataset_dir)
    if not target_dir.exists():
        print(f"[FAIL] Dataset directory does not exist: {target_dir}")
        return False

    print("==================================================================")
    print(f"   DATASET INTEGRITY & QUALITY VERIFICATION: {target_dir.name}   ")
    print("==================================================================")

    manifest_jsonl = target_dir / "manifest.jsonl"
    metadata_csv = target_dir / "metadata.csv"

    if not manifest_jsonl.exists():
        print(f"[FAIL] Missing manifest.jsonl at {manifest_jsonl}")
        return False
    if not metadata_csv.exists():
        print(f"[FAIL] Missing metadata.csv at {metadata_csv}")
        return False

    # Read manifest records
    with open(manifest_jsonl, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    with open(metadata_csv, "r", encoding="utf-8-sig") as f:
        csv_rows = list(csv.DictReader(f))

    if len(records) != len(csv_rows):
        print(f"[FAIL] Count mismatch: JSONL has {len(records)} items, CSV has {len(csv_rows)} rows")
        return False

    print(f"[OK] Manifest files loaded: {len(records)} records found.")

    # Check each audio file
    errors = []
    warnings = []

    for idx, item in enumerate(records, 1):
        rel_path = item["relative_path"]
        abs_path = target_dir / rel_path

        if not abs_path.exists():
            errors.append(f"Missing audio file: {rel_path}")
            continue

        try:
            info = sf.info(abs_path)
            # Check format
            if info.format != "WAV":
                errors.append(f"{rel_path}: Invalid format {info.format}, expected WAV")
            if info.samplerate != 24000:
                warnings.append(f"{rel_path}: Sample rate is {info.samplerate}Hz (expected 24000Hz)")
            if info.channels != 1:
                warnings.append(f"{rel_path}: Channels count {info.channels} (expected 1 mono)")

            data, sr = sf.read(abs_path)
            peak = float(np.max(np.abs(data)))
            rms = float(np.sqrt(np.mean(data**2)))

            if peak > 0.99:
                warnings.append(f"{rel_path}: Potential clipping detected (peak={peak:.3f})")
            if rms < 0.005:
                warnings.append(f"{rel_path}: Audio signal is very low/silent (rms={rms:.5f})")

        except Exception as e:
            errors.append(f"{rel_path}: Failed to read audio: {e}")

    # Summary
    print(f"\nVerification Results:")
    print(f"- Total audio files verified: {len(records)}")
    print(f"- Errors:   {len(errors)}")
    print(f"- Warnings: {len(warnings)}")

    if warnings:
        print("\nWarnings:")
        for w in warnings[:10]:
            print(f"  [WARN] {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings.")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  [ERR] {e}")
        return False

    print("\n[SUCCESS] Dataset verification PASSED with 0 errors!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify elderly voice dataset structure and quality.")
    parser.add_argument("--dir", type=str, default=str(OUTPUT_DATASET_DIR), help="Dataset directory to verify")
    args = parser.parse_args()

    success = verify_dataset(args.dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
