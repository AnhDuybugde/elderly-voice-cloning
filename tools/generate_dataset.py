#!/usr/bin/env python3
"""CLI tool to generate elderly voice dataset according to multi-region matrix."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import get_speakers_config, get_prompts_config, OUTPUT_DATASET_DIR
from src.synthesis.engine import ZeroTTSSynthesizer, FallbackSynthesizer
from src.pipeline.generator import ElderlyVoiceDatasetGenerator
from src.pipeline.manifest import generate_summary_report


def main():
    parser = argparse.ArgumentParser(description="Generate multi-region Vietnamese elderly voice dataset.")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DATASET_DIR), help="Output directory path")
    parser.add_argument("--speaker-id", type=str, default=None, help="Specific speaker ID (e.g. spk_nam_01)")
    parser.add_argument("--category-id", type=str, default=None, help="Specific category ID (e.g. giong_noi_keu_cuu)")
    parser.add_argument("--sample-rate", type=int, default=24000, help="Target audio sample rate (Hz)")
    parser.add_argument("--use-fallback", action="store_true", help="Use procedural tone synthesizer instead of ZeroTTS")
    args = parser.parse_args()

    print("==================================================================")
    print("   ELDERLY VOICE CLONING - VIETNAMESE MULTI-REGION DATASET GEN    ")
    print("==================================================================")

    synthesizer = FallbackSynthesizer() if args.use_fallback else ZeroTTSSynthesizer()
    generator = ElderlyVoiceDatasetGenerator(
        output_dir=args.output_dir,
        synthesizer=synthesizer,
        sample_rate=args.sample_rate,
    )

    speakers = get_speakers_config()
    if args.speaker_id:
        speakers = [s for s in speakers if s.id == args.speaker_id]
        if not speakers:
            print(f"Error: Speaker '{args.speaker_id}' not found in configs/speakers.yaml")
            sys.exit(1)

    categories = get_prompts_config()
    if args.category_id:
        categories = [c for c in categories if c.id.value == args.category_id]
        if not categories:
            print(f"Error: Category '{args.category_id}' not found in configs/prompts.yaml")
            sys.exit(1)

    print(f"-> Speakers count: {len(speakers)}")
    print(f"-> Categories count: {len(categories)}")
    print(f"-> Target sample rate: {args.sample_rate} Hz")
    print(f"-> Output directory: {args.output_dir}\n")

    def on_progress(meta):
        print(f"  [GEN] [{meta.speaker_name}] [{meta.category}] -> {meta.file_name} (F0={meta.f0_mean_hz}Hz, Jitter={meta.jitter_pct}%, Shimmer={meta.shimmer_pct}%)")

    manifest = generator.generate_all(speakers=speakers, categories=categories, progress_callback=on_progress)

    report = generate_summary_report(manifest)
    print("\n------------------------------------------------------------------")
    print("                      GENERATION SUMMARY                          ")
    print("------------------------------------------------------------------")
    print(f"Total audio files generated: {report['total_samples']}")
    print(f"Total duration: {report['total_duration_sec']}s ({report['total_duration_min']} min)")
    print(f"Speakers included: {report['speakers_count']}")
    print(f"Manifest JSONL: {Path(args.output_dir) / 'manifest.jsonl'}")
    print(f"Metadata CSV:   {Path(args.output_dir) / 'metadata.csv'}")
    print("------------------------------------------------------------------\n")


if __name__ == "__main__":
    main()
