#!/usr/bin/env python3
"""CLI tool to generate the elderly voice dataset (v3.0 WORLD aging + QC gate).

Examples:
    python3 tools/generate_dataset.py                       # benchmark greeting x 12 speakers
    python3 tools/generate_dataset.py --full --variants 3   # 12 speakers x 15 prompts x 3 takes
    python3 tools/generate_dataset.py --full --speakers spk_05_bac_hao spk_12_nam_nuong
    python3 tools/generate_dataset.py --full --with-noise   # + noisy copies for giong_co_nhieu
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import OUTPUT_DATASET_DIR, get_prompts_config, get_speakers_config  # noqa: E402
from src.pipeline.generator import ElderlyVoiceDatasetGenerator  # noqa: E402
from src.pipeline.manifest import generate_summary_report  # noqa: E402
from src.synthesis.engine import FallbackSynthesizer, ZeroTTSSynthesizer  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Generate multi-region Vietnamese elderly voice dataset.")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DATASET_DIR), help="Output directory path")
    parser.add_argument("--speakers", nargs="*", default=None, help="Speaker IDs to generate (default: all)")
    parser.add_argument("--speaker-id", type=str, default=None, help="[legacy] single speaker ID")
    parser.add_argument("--full", action="store_true", help="Full scenario dataset (all prompts x variants)")
    parser.add_argument("--variants", type=int, default=3, help="Takes per prompt in --full mode (default 3)")
    parser.add_argument("--with-noise", action="store_true", help="Also write noisy copies for prompts with a noise profile")
    parser.add_argument("--skip-qc", action="store_true", help="Disable QC gate, ASR and speaker-similarity report")
    parser.add_argument("--max-attempts", type=int, default=3, help="QC retries per utterance (default 3)")
    parser.add_argument("--sample-rate", type=int, default=48000, help="Target audio sample rate in Hz")
    parser.add_argument("--use-fallback", action="store_true", help="Use fallback harmonic synthesizer instead of ZeroTTS")
    args = parser.parse_args()

    print("==================================================================")
    print("   ELDERLY VOICE CLONING v3.0 - VIETNAMESE MULTI-REGION DATASET   ")
    print("==================================================================")

    synthesizer = FallbackSynthesizer() if args.use_fallback else ZeroTTSSynthesizer()
    qc_flag = False if args.skip_qc else None  # None = auto (on for the neural engine)
    generator = ElderlyVoiceDatasetGenerator(
        output_dir=args.output_dir,
        synthesizer=synthesizer,
        sample_rate=args.sample_rate,
        use_asr=qc_flag,
        use_embedder=qc_flag,
        run_qc=qc_flag,
        max_attempts=args.max_attempts,
    )

    speakers = get_speakers_config()
    wanted = set(args.speakers or []) | ({args.speaker_id} if args.speaker_id else set())
    if wanted:
        speakers = [s for s in speakers if s.id in wanted]
        missing = wanted - {s.id for s in speakers}
        if missing:
            print(f"Error: unknown speaker id(s): {sorted(missing)}")
            sys.exit(1)

    categories = get_prompts_config()
    n_prompts = sum(len(c.prompts) for c in categories)
    expected = len(speakers) * (1 + (n_prompts * args.variants if args.full else 0))
    print(f"-> Speakers: {len(speakers)} | Mode: {'FULL' if args.full else 'benchmark greeting'}")
    if args.full:
        print(f"-> Prompts: {n_prompts} x {args.variants} variants (+1 greeting) -> ~{expected} clean files")
    print(f"-> QC gate: {'off' if args.skip_qc else 'on'} | Noise copies: {'on' if args.with_noise else 'off'}")
    print(f"-> Output directory: {args.output_dir}\n")

    t0 = time.time()
    counter = {"n": 0}

    def on_progress(meta):
        counter["n"] += 1
        qc = {True: "PASS", False: "FAIL", None: "----"}[meta.qc_pass]
        elapsed = time.time() - t0
        print(
            f"  [{counter['n']:4d}] {qc} {meta.speaker_id:20s} {meta.relative_path.split('/')[-1]:58s} "
            f"F0={meta.f0_mean_hz:6.1f} jit={meta.jitter_pct:4.2f}% shim={meta.shimmer_pct:5.2f}% "
            f"HNR={meta.hnr_db:5.1f} rate={meta.speech_rate_syl_s or 0:4.2f} CER={meta.cer if meta.cer is not None else '-'} "
            f"({elapsed/60:.1f} min)",
            flush=True,
        )
        if meta.qc_pass is False and meta.qc_reasons:
            print(f"         reasons: {'; '.join(meta.qc_reasons)}", flush=True)

    if args.full:
        manifest = generator.generate_all(
            speakers=speakers, categories=categories, n_variants=args.variants,
            with_noise=args.with_noise, progress_callback=on_progress,
        )
    else:
        manifest = generator.generate_all_benchmark(speakers=speakers, progress_callback=on_progress)

    clean = [m for m in manifest if m.noise_type == "clean"]
    report = generate_summary_report(clean)
    print("\n------------------------------------------------------------------")
    print("                      GENERATION SUMMARY                          ")
    print("------------------------------------------------------------------")
    print(f"Clean audio files:  {report['total_samples']}  (noisy copies: {len(manifest) - len(clean)})")
    print(f"Total duration:     {report['total_duration_sec']}s ({report['total_duration_min']} min)")
    print(f"Speakers included:  {report['speakers_count']}")
    if report.get("qc_pass_rate") is not None:
        print(f"QC pass rate:       {report['qc_pass_rate'] * 100:.1f}%")
    print(f"Elapsed:            {(time.time() - t0) / 60:.1f} min")
    print(f"Manifest JSONL:     {Path(args.output_dir) / 'manifest.jsonl'}")
    print("Next: python3 tools/verify_dataset.py --report")
    print("------------------------------------------------------------------\n")


if __name__ == "__main__":
    main()
