#!/usr/bin/env python3
"""Calibrate DSP strengths so *measured* Praat metrics hit each gender x age-bin target.

DSP inputs are not the same as measured outputs (e.g. 2% injected F0 noise does not read
as 2% Praat jitter after WORLD resynthesis). For every gender x age bin this tool:

    1. synthesizes a few reference sentences with a neutral voice mix (cached per gender)
    2. sweeps a scale factor for each DSP knob independently
         jitter_pct -> measured jitter_pct
         shimmer_db -> measured shimmer_pct
         breathiness -> measured hnr_db
    3. keeps the factor whose mean measurement is closest to the target
    4. writes the calibrated values into configs/acoustic_profiles.yaml (`calibrated:`)

Re-run this when real volunteer recordings arrive: replace the `target` values with the
measured real-speaker distribution and calibrate again.

Usage:
    python3 tools/calibrate_aging.py               # calibrate and write config
    python3 tools/calibrate_aging.py --dry-run     # print only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import CONFIGS_DIR  # noqa: E402
from src.core.schema import VoiceAgingParams  # noqa: E402
from src.metrics.acoustic_features import analyze_audio_sample, count_vi_syllables, speech_activity  # noqa: E402
from src.synthesis.voice_profile import clear_profile_cache, get_profile  # noqa: E402
from src.synthesis.world_aging import age_voice  # noqa: E402

SENTENCES = [
    "Gia An ơi, hôm nay mấy giờ tôi phải uống thuốc huyết áp vậy?",
    "Bật đèn phòng khách giúp tôi với, trời tối rồi.",
    "Tối nay lúc tám giờ nhắc tôi uống sữa chua nhé.",
]
NEUTRAL_MIX = {
    "nam": {"huuduc": 0.5, "giahuy": 0.25, "quangminh": 0.25},
    "nu": {"kimoanh": 0.5, "baotrang": 0.3, "maichi": 0.2},
}
FACTORS = [0.5, 0.75, 1.0, 1.3, 1.7, 2.2, 2.8]
KNOBS = [("jitter_pct", "jitter_pct"), ("shimmer_db", "shimmer_pct"), ("breathiness", "hnr_db")]
BINS = ["50_59", "60_69", "70_79", "80_plus"]


def _base_params(dsp: dict, target: dict, src_rate: float) -> dict:
    return dict(
        target_f0_hz=target["f0_hz"],
        jitter_pct=dsp["jitter_pct"],
        shimmer_db=dsp["shimmer_db"],
        tremor_rate_hz=5.2,
        tremor_f0_depth=dsp["tremor_f0_depth"],
        tremor_amp_depth=dsp["tremor_amp_depth"],
        breathiness=dsp["breathiness"],
        formant_warp=dsp["formant_warp"],
        spectral_tilt_db_oct=dsp["spectral_tilt_db_oct"],
        creak_prob=dsp["creak_prob"],
        voice_break_prob=0.0,
        tempo_scale=float(np.clip(target["speech_rate_syl_s"] / max(src_rate, 1e-3), 0.55, 1.15)),
        pause_scale=dsp["pause_scale"],
        inhale_prob=0.0,
        chest_warmth=dsp["chest_warmth"],
        hf_cutoff_hz=dsp["hf_cutoff_hz"],
    )


def _measure(clips, gender, params_kw, seed=11) -> dict:
    vals = {"jitter_pct": [], "shimmer_pct": [], "hnr_db": []}
    for (audio, sr, text, src_rate) in clips:
        kw = dict(params_kw)
        kw["tempo_scale"] = float(np.clip(params_kw["_target_rate"] / max(src_rate, 1e-3), 0.55, 1.15))
        kw.pop("_target_rate")
        y = age_voice(audio, sr, VoiceAgingParams(**kw), rng=np.random.default_rng(seed), gender=gender)
        m = analyze_audio_sample(y, sr, gender=gender, text=text)
        for k in vals:
            vals[k].append(m[k])
    return {k: float(np.mean(v)) for k, v in vals.items()}


def synthesize_reference_clips(gender: str, use_fallback: bool):
    from src.synthesis.engine import FallbackSynthesizer, ZeroTTSSynthesizer

    synth = FallbackSynthesizer() if use_fallback else ZeroTTSSynthesizer()
    clips = []
    for i, text in enumerate(SENTENCES):
        audio, sr = synth.synthesize(text, voice_mix=NEUTRAL_MIX[gender], seed=100 + i, target_sr=48000)
        act = speech_activity(audio, sr)
        rate = count_vi_syllables(text) / act["active_sec"] if act["active_sec"] > 0 else 4.5
        clips.append((audio, sr, text, rate))
    return clips


def calibrate(use_fallback: bool = False, verbose: bool = True) -> dict:
    clear_profile_cache()
    result: dict = {}
    for gender in ("nam", "nu"):
        clips = synthesize_reference_clips(gender, use_fallback)
        result[gender] = {}
        for age_bin in BINS:
            prof = get_profile(gender, age_bin)
            # Always start from the *uncalibrated* base so repeated runs are stable
            dsp = dict(prof["dsp"])
            dsp.update(_raw_dsp(gender, age_bin))
            target = prof["target"]
            base = _base_params(dsp, target, 4.5)
            base["_target_rate"] = target["speech_rate_syl_s"]

            chosen = {}
            for knob, metric in KNOBS:
                if metric not in target:
                    continue
                best_f, best_err, best_val = 1.0, float("inf"), None
                for f in FACTORS:
                    kw = dict(base)
                    kw[knob] = base[knob] * f
                    meas = _measure(clips, gender, kw)
                    err = abs(meas[metric] - target[metric])
                    if err < best_err:
                        best_f, best_err, best_val = f, err, meas[metric]
                chosen[knob] = round(base[knob] * best_f, 4)
                if verbose:
                    print(f"  {gender:3s} {age_bin:8s} {knob:12s} x{best_f:<4} -> {metric}={best_val:.2f} (target {target[metric]})")
            result[gender][age_bin] = chosen
    return result


def _raw_dsp(gender: str, age_bin: str) -> dict:
    with open(CONFIGS_DIR / "acoustic_profiles.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return dict(cfg["profiles"][gender][age_bin]["dsp"])


def write_calibration(calibrated: dict, path: Path = CONFIGS_DIR / "acoustic_profiles.yaml") -> None:
    text = path.read_text(encoding="utf-8")
    marker = "\ncalibrated:"
    idx = text.find(marker)
    if idx < 0:
        raise RuntimeError("`calibrated:` section not found in acoustic_profiles.yaml")
    lines = ["", "calibrated:"]
    for gender, bins in calibrated.items():
        lines.append(f"  {gender}:")
        for age_bin, knobs in bins.items():
            inner = ", ".join(f"{k}: {v}" for k, v in knobs.items())
            lines.append(f'    "{age_bin}": {{{inner}}}')
    path.write_text(text[:idx] + "\n".join(lines) + "\n", encoding="utf-8")
    clear_profile_cache()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="Print results without writing the config")
    ap.add_argument("--use-fallback", action="store_true", help="Use the harmonic fallback synthesizer (testing only)")
    args = ap.parse_args()

    print("Calibrating WORLD aging strengths against acoustic targets...")
    cal = calibrate(use_fallback=args.use_fallback)
    if args.dry_run:
        print(yaml.safe_dump(cal, allow_unicode=True, sort_keys=False))
    else:
        write_calibration(cal)
        print("-> Wrote `calibrated:` section to configs/acoustic_profiles.yaml")


if __name__ == "__main__":
    main()
