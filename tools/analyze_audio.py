#!/usr/bin/env python3
"""Acoustic inspection tool: prints F0, jitter, shimmer, HNR for an audio file."""

import argparse
import sys
from pathlib import Path
import soundfile as sf

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.metrics.acoustic_features import analyze_audio_sample


def main():
    parser = argparse.ArgumentParser(description="Analyze acoustic properties of an audio file.")
    parser.add_argument("audio_path", type=str, help="Path to WAV audio file")
    parser.add_argument("--gender", choices=["nam", "nu"], default=None, help="Speaker gender (sets pitch floor/ceiling)")
    parser.add_argument("--text", type=str, default=None, help="Transcript (enables speech-rate)")
    parser.add_argument("--asr", action="store_true", help="Also transcribe with faster-whisper and compute CER (needs --text)")
    args = parser.parse_args()

    path = Path(args.audio_path)
    if not path.exists():
        print(f"Error: File not found at {path}")
        sys.exit(1)

    audio, sr = sf.read(path)
    result = analyze_audio_sample(audio, sr, gender=args.gender, text=args.text)

    print("------------------------------------------------------------------")
    print(f"   ACOUSTIC REPORT: {path.name}")
    print("------------------------------------------------------------------")
    print(f"Sample Rate:         {sr} Hz")
    print(f"Duration:            {result['duration_sec']} seconds")
    print(f"Fundamental Freq F0: {result['f0_mean_hz']} Hz (std: {result['f0_std_hz']} Hz)")
    print(f"Local Jitter:        {result['jitter_pct']}%")
    print(f"Local Shimmer:       {result['shimmer_pct']}%")
    print(f"Harmonic-to-Noise:   {result['hnr_db']} dB")
    print(f"CPPS:                {result['cpps_db']} dB")
    print(f"Speech rate:         {result['speech_rate_syl_s']} syl/s" + ("" if args.text else "  (pass --text)"))
    print(f"Pause ratio:         {result['pause_ratio']} (mean pause {result['mean_pause_ms']} ms)")
    print(f"Peak level:          {result['peak_dbfs']} dBFS")
    if args.asr and args.text:
        from src.metrics.intelligibility import measure_intelligibility

        intel = measure_intelligibility(audio, sr, args.text)
        print(f"ASR transcript:      {intel['asr_text']}")
        print(f"CER / WER:           {intel['cer'] * 100:.1f}% / {intel['wer'] * 100:.1f}%")
    print("------------------------------------------------------------------")


if __name__ == "__main__":
    main()
