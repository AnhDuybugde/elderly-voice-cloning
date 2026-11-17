"""Per-sample quality gate for synthetic elderly speech.

A sample passes when:
- F0 / jitter / shimmer / HNR / speech-rate fall inside the gender x age-bin QC range
  (configs/acoustic_profiles.yaml: profiles.<gender>.<bin>.qc)
- ASR character error rate <= CER_MAX (catches TTS hallucinations: skipped / repeated words)
- no clipping, sane duration per syllable
"""

from __future__ import annotations

from typing import Optional

CER_MAX = 0.15  # ASR mishears the wake-word "Gia An" even on clean TTS (~5-9% CER baseline)
PEAK_MAX_DBFS = -0.5
SEC_PER_SYLLABLE = (0.15, 0.95)
MIN_SYLLABLES_FOR_RATE = 10  # speech rate on very short calls ("Cứu tôi với!") is not reliable

_METRIC_LABELS = {
    "f0_hz": "f0_mean_hz",
    "jitter_pct": "jitter_pct",
    "shimmer_pct": "shimmer_pct",
    "hnr_db": "hnr_db",
    "speech_rate_syl_s": "speech_rate_syl_s",
}


def evaluate_sample(
    metrics: dict,
    qc_ranges: dict,
    n_syllables: int,
    cer: Optional[float] = None,
    cer_max: float = CER_MAX,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    for key, metric_name in _METRIC_LABELS.items():
        if key not in qc_ranges:
            continue
        if key == "speech_rate_syl_s" and n_syllables < MIN_SYLLABLES_FOR_RATE:
            continue
        lo, hi = qc_ranges[key]
        val = metrics.get(metric_name)
        if val is None or val == 0:
            reasons.append(f"{metric_name}=missing")
        elif not (lo <= val <= hi):
            reasons.append(f"{metric_name}={val:g} not in [{lo}, {hi}]")

    if cer is not None and cer > cer_max:
        reasons.append(f"cer={cer:.3f} > {cer_max}")

    if metrics.get("peak_dbfs", -99) > PEAK_MAX_DBFS:
        reasons.append(f"clipping peak={metrics['peak_dbfs']} dBFS")

    if n_syllables:
        per_syl = metrics.get("duration_sec", 0.0) / n_syllables
        if not (SEC_PER_SYLLABLE[0] <= per_syl <= SEC_PER_SYLLABLE[1] * 1.6):
            reasons.append(f"duration/syllable={per_syl:.2f}s abnormal")

    return len(reasons) == 0, reasons


def severity(reasons: list[str]) -> int:
    """Rank failures so the best of several attempts can be kept (lower = better)."""
    score = 0
    for r in reasons:
        if r.startswith("cer") or r.startswith("duration") or r.startswith("clipping"):
            score += 10
        else:
            score += 1
    return score


def requalify_manifest(dataset_dir, asr=None, verbose: bool = True) -> dict:
    """Re-apply the *current* QC rules to failed records (no re-synthesis).

    Re-transcribes failed samples (CER definition may have changed), re-evaluates them
    against the current QC ranges and rewrites manifest.jsonl / metadata.csv in place.
    """
    import json
    from pathlib import Path

    import soundfile as sf

    from src.core.schema import AudioSampleMetadata
    from src.metrics.acoustic_features import count_vi_syllables
    from src.metrics.intelligibility import VietnameseASR, cer
    from src.pipeline.manifest import export_manifest_csv, export_manifest_jsonl
    from src.synthesis.voice_profile import get_profile

    root = Path(dataset_dir)
    path = root / "manifest.jsonl"
    records = [AudioSampleMetadata(**json.loads(l)) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    asr = asr or VietnameseASR()
    changed = {"rechecked": 0, "now_pass": 0}
    for r in records:
        if r.qc_pass is not False:
            continue
        changed["rechecked"] += 1
        audio, sr = sf.read(root / r.relative_path)
        spoken = r.spoken_text or r.utterance_text
        r.asr_text = asr.transcribe(audio, sr)
        r.cer = round(cer(spoken, r.asr_text), 4)
        metrics = {
            "f0_mean_hz": r.f0_mean_hz, "jitter_pct": r.jitter_pct, "shimmer_pct": r.shimmer_pct,
            "hnr_db": r.hnr_db, "speech_rate_syl_s": r.speech_rate_syl_s, "duration_sec": r.duration_sec,
        }
        ok, reasons = evaluate_sample(metrics, get_profile(r.gender, r.age_bin)["qc"], count_vi_syllables(spoken), r.cer)
        r.qc_pass, r.qc_reasons = ok, (reasons or None)
        if ok:
            changed["now_pass"] += 1
        if verbose:
            print(f"  {'PASS' if ok else 'FAIL'} {r.relative_path}  CER={r.cer}  {'; '.join(reasons)}")
    export_manifest_jsonl(records, path)
    export_manifest_csv(records, root / "metadata.csv")
    return changed
