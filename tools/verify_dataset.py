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
            if info.samplerate not in [24000, 48000]:
                warnings.append(f"{rel_path}: Non-standard sample rate {info.samplerate}Hz")
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

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  [ERR] {e}")
        return False

    print("\n[SUCCESS] Dataset verification PASSED with 0 errors!")
    return True


AGE_BINS = ["50_59", "60_69", "70_79", "80_plus"]
REPORT_METRICS = [
    ("f0_mean_hz", "F0 (Hz)", None),
    ("jitter_pct", "Jitter (%)", "up"),
    ("shimmer_pct", "Shimmer (%)", "up"),
    ("hnr_db", "HNR (dB)", "down"),
    ("cpps_db", "CPPS (dB)", "down"),
    ("speech_rate_syl_s", "Rate (syl/s)", "down"),
    ("pause_ratio", "Pause ratio", "up"),
]
SIMILARITY_WARN = 0.95  # WavLM-SV: distinct TTS base voices already score 0.86-0.92


def _mean(values):
    vals = [v for v in values if v is not None]
    return float(np.mean(vals)) if vals else float("nan")


def build_report(dataset_dir: Path | str) -> str:
    """Markdown report: per gender x age-bin acoustics, age trends, QC, identity diversity."""
    target_dir = Path(dataset_dir)
    with open(target_dir / "manifest.jsonl", "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    clean = [r for r in records if r.get("noise_type", "clean") == "clean"]

    lines = [f"# Báo cáo dataset giọng người cao tuổi — `{target_dir.name}`", ""]
    lines.append(f"- Số file sạch: **{len(clean)}**, số người nói: **{len({r['speaker_id'] for r in clean})}**")
    total_min = sum(r["duration_sec"] for r in clean) / 60.0
    lines.append(f"- Tổng thời lượng: **{total_min:.1f} phút**")
    versions = sorted({r.get("model_version", "?") for r in clean})
    lines.append(f"- Model version: {', '.join(versions)}")

    qc_known = [r for r in clean if r.get("qc_pass") is not None]
    if qc_known:
        rate = sum(1 for r in qc_known if r["qc_pass"]) / len(qc_known)
        lines.append(f"- Tỉ lệ pass QC: **{rate * 100:.1f}%** ({sum(1 for r in qc_known if r['qc_pass'])}/{len(qc_known)})")
        retries = sum(1 for r in qc_known if (r.get("attempts") or 1) > 1)
        lines.append(f"- Số mẫu phải sinh lại (retry): {retries}")
    cers = [r["cer"] for r in clean if r.get("cer") is not None]
    if cers:
        lines.append(f"- CER trung bình (faster-whisper): **{np.mean(cers) * 100:.1f}%**, median {np.median(cers) * 100:.1f}%, max {np.max(cers) * 100:.1f}%")
    lines.append("")

    # --- Per gender x age bin table + trend check ---
    lines.append("## 1. Đặc trưng âm học theo giới tính × nhóm tuổi (Praat)")
    lines.append("")
    trend_notes = []
    for gender, label in (("nam", "Nam"), ("nu", "Nữ")):
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Nhóm tuổi | N | " + " | ".join(m[1] for m in REPORT_METRICS) + " |")
        lines.append("|---|---:|" + "---:|" * len(REPORT_METRICS))
        bin_means = {}
        for b in AGE_BINS:
            rows = [r for r in clean if r["gender"] == gender and r["age_bin"] == b]
            if not rows:
                continue
            means = {k: _mean(r.get(k) for r in rows) for k, _, _ in REPORT_METRICS}
            bin_means[b] = means
            cells = " | ".join(f"{means[k]:.2f}" for k, _, _ in REPORT_METRICS)
            lines.append(f"| {b} | {len(rows)} | {cells} |")
        lines.append("")
        bins_present = [b for b in AGE_BINS if b in bin_means]
        for k, name, direction in REPORT_METRICS:
            if not direction or len(bins_present) < 2:
                continue
            seq = [bin_means[b][k] for b in bins_present]
            first, last = seq[0], seq[-1]
            ok = last > first if direction == "up" else last < first
            mono = all((b2 >= b1) if direction == "up" else (b2 <= b1) for b1, b2 in zip(seq, seq[1:]))
            status = "tăng dần đều" if (mono and direction == "up") else "giảm dần đều" if mono else ("đúng xu hướng (không đơn điệu)" if ok else "SAI xu hướng")
            trend_notes.append(f"- {label} · {name}: {' → '.join(f'{v:.2f}' for v in seq)} — {status}")
    lines.append("## 2. Kiểm tra xu hướng lão hoá (50–59 → 80+)")
    lines.append("")
    lines.extend(trend_notes or ["- (không đủ nhóm tuổi để so sánh)"])
    lines.append("")

    # --- Per speaker ---
    lines.append("## 3. Theo từng người nói")
    lines.append("")
    lines.append("| Speaker | Tuổi | Giới | Vùng | N | F0 | Jitter | Shimmer | HNR | Rate | CER | Sim→centroid | QC pass |")
    lines.append("|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for spk in sorted({r["speaker_id"] for r in clean}, key=lambda s: next(r["age"] for r in clean if r["speaker_id"] == s)):
        rows = [r for r in clean if r["speaker_id"] == spk]
        r0 = rows[0]
        qc_rows = [r for r in rows if r.get("qc_pass") is not None]
        qc_txt = f"{sum(1 for r in qc_rows if r['qc_pass'])}/{len(qc_rows)}" if qc_rows else "-"
        cer_txt = f"{_mean(r.get('cer') for r in rows) * 100:.1f}%" if any(r.get("cer") is not None for r in rows) else "-"
        sim = _mean(r.get("speaker_sim_to_centroid") for r in rows)
        lines.append(
            f"| {r0['speaker_name']} | {r0['age']} | {r0['gender']} | {r0['region']} | {len(rows)} | "
            f"{_mean(r['f0_mean_hz'] for r in rows):.1f} | {_mean(r['jitter_pct'] for r in rows):.2f} | "
            f"{_mean(r['shimmer_pct'] for r in rows):.2f} | {_mean(r['hnr_db'] for r in rows):.1f} | "
            f"{_mean(r.get('speech_rate_syl_s') for r in rows):.2f} | {cer_txt} | "
            f"{'-' if np.isnan(sim) else f'{sim:.3f}'} | {qc_txt} |"
        )
    lines.append("")

    # --- Identity diversity ---
    sim_path = target_dir / "reports" / "speaker_similarity.json"
    lines.append("## 4. Độ khác biệt danh tính giữa các cụ (WavLM-SV cosine giữa centroid)")
    lines.append("")
    if sim_path.exists():
        sim = json.loads(sim_path.read_text(encoding="utf-8"))
        names, mat = sim["speakers"], np.array(sim["matrix"])
        gender_of = {r["speaker_id"]: r["gender"] for r in clean}
        for g, label in (("nam", "Nam"), ("nu", "Nữ")):
            idx = [i for i, n in enumerate(names) if gender_of.get(n) == g]
            if len(idx) < 2:
                continue
            sub = mat[np.ix_(idx, idx)]
            iu = np.triu_indices(len(idx), 1)
            lines.append(f"- {label}: cosine trung bình giữa các cặp = **{sub[iu].mean():.3f}**, cao nhất = {sub[iu].max():.3f}")
        close = [
            (names[i], names[j], mat[i, j])
            for i in range(len(names)) for j in range(i + 1, len(names))
            if mat[i, j] > SIMILARITY_WARN
        ]
        lines.append(f"- Cặp vượt ngưỡng cảnh báo {SIMILARITY_WARN}: " + (", ".join(f"{a}~{b} ({v:.3f})" for a, b, v in close) if close else "**không có**"))
        lines.append("- Mốc tham chiếu: v2.0 có cosine 0.95–0.99 giữa các cặp cùng giới; các voice pack gốc khác nhau của ZeroTTS đo được 0.86–0.92.")
    else:
        lines.append("- (chưa có reports/speaker_similarity.json — chạy generator không dùng --skip-qc)")
    lines.append("")

    # --- QC failures ---
    fails = [r for r in qc_known if not r["qc_pass"]]
    lines.append("## 5. Mẫu không qua QC")
    lines.append("")
    if fails:
        reason_count: dict[str, int] = {}
        for r in fails:
            for reason in r.get("qc_reasons") or []:
                key = reason.split("=")[0]
                reason_count[key] = reason_count.get(key, 0) + 1
        lines.append("Lý do (đếm theo chỉ số): " + ", ".join(f"`{k}` × {v}" for k, v in sorted(reason_count.items(), key=lambda x: -x[1])))
        lines.append("")
        for r in fails[:30]:
            lines.append(f"- `{r['relative_path']}` — {'; '.join(r.get('qc_reasons') or [])}")
        if len(fails) > 30:
            lines.append(f"- … và {len(fails) - 30} mẫu khác (xem manifest.jsonl, trường `qc_reasons`)")
    else:
        lines.append("- Không có.")
    lines.append("")

    lines.append("## 6. Giới hạn đã biết (đọc trước khi dùng kết quả test)")
    lines.append("")
    lines.extend([
        "- **Giọng vùng miền**: thanh điệu & phụ âm cuối địa phương phụ thuộc model ZeroTTS (thiên về giọng chuẩn). "
        "v3.0 chỉ thêm từ vựng địa phương (`spoken_text`); giọng vùng thật cần fine-tune/VC trên dữ liệu tình nguyện viên.",
        "- **Mốc âm học lấy từ y văn**, chưa đối chiếu với người thật cùng nhóm. Khi có dữ liệu thật: cập nhật `target` và chạy lại `tools/calibrate_aging.py`.",
        "- **Giọng nam gốc** đã có jitter/shimmer cao (~3% / ~8%) do codec; nhóm 50–69 nam vì vậy 'thô' hơn y văn.",
        "- **Giọng nữ có tuổi** chỉ có 2 voice pack (`kimoanh`, `baotrang`): độ đa dạng nữ dựa nhiều vào DSP (F0, formant).",
        "- **CER** đo bằng faster-whisper `small`; ASR hay nghe nhầm tên riêng \"Gia An\" kể cả trên giọng gốc, nên ngưỡng QC CER là 15%.",
        "- Synthetic dễ hơn người thật ở: phát âm vẫn rõ (không mất răng/méo phụ âm), không có hụt hơi giữa từ, không ho/hắng giọng.",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Verify elderly voice dataset structure and quality.")
    parser.add_argument("--dir", type=str, default=str(OUTPUT_DATASET_DIR), help="Dataset directory to verify")
    parser.add_argument("--report", action="store_true", help="Also write reports/dataset_report.md")
    parser.add_argument("--requalify", action="store_true", help="Re-apply current QC rules to failed samples (re-runs ASR, no re-synthesis)")
    args = parser.parse_args()

    if args.requalify:
        from src.pipeline.qc import requalify_manifest

        print("Re-qualifying failed samples with current QC rules...")
        res = requalify_manifest(args.dir)
        print(f"-> rechecked {res['rechecked']}, now passing {res['now_pass']}\n")

    success = verify_dataset(args.dir)
    if args.report and Path(args.dir, "manifest.jsonl").exists():
        report = build_report(args.dir)
        out = Path(args.dir) / "reports" / "dataset_report.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\n[REPORT] Written to {out}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
