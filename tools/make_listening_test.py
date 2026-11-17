#!/usr/bin/env python3
"""Build a blind listening test from the generated dataset.

Creates:
    <out>/audio/q001.wav ...        anonymised copies (shuffled, no speaker/age in the name)
    <out>/answer_sheet.csv          what listeners fill in: estimated age, naturalness MOS (1-5),
                                    "same speaker as question X?" pairs
    <out>/answer_key.csv            hidden mapping -> speaker, true age, file (keep away from listeners)

Then score with:  python3 tools/make_listening_test.py --score <out>/answer_sheet_filled.csv --key <out>/answer_key.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import OUTPUT_DATASET_DIR  # noqa: E402


def build(dataset_dir: Path, out_dir: Path, per_speaker: int, n_pairs: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    records = [json.loads(l) for l in (dataset_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    records = [r for r in records if r.get("noise_type", "clean") == "clean" and r.get("qc_pass") is not False]

    chosen = []
    for spk in sorted({r["speaker_id"] for r in records}):
        rows = [r for r in records if r["speaker_id"] == spk]
        idx = rng.choice(len(rows), size=min(per_speaker, len(rows)), replace=False)
        chosen.extend(rows[i] for i in idx)
    order = rng.permutation(len(chosen))
    chosen = [chosen[i] for i in order]

    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    key_rows, sheet_rows = [], []
    for qi, r in enumerate(chosen, 1):
        qid = f"q{qi:03d}"
        shutil.copy2(dataset_dir / r["relative_path"], audio_dir / f"{qid}.wav")
        key_rows.append({"question": qid, "speaker_id": r["speaker_id"], "age": r["age"], "gender": r["gender"],
                         "region": r["region"], "relative_path": r["relative_path"]})
        sheet_rows.append({"question": qid, "estimated_age": "", "naturalness_mos_1_5": "", "notes": ""})

    # Same/different speaker pairs (half same, half different)
    by_spk: dict[str, list[str]] = {}
    for k in key_rows:
        by_spk.setdefault(k["speaker_id"], []).append(k["question"])
    pair_rows = []
    spks = [s for s, q in by_spk.items() if len(q) >= 2]
    for p in range(n_pairs):
        if p % 2 == 0 and spks:
            s = spks[rng.integers(len(spks))]
            a, b = rng.choice(by_spk[s], size=2, replace=False)
        else:
            a, b = rng.choice([k["question"] for k in key_rows], size=2, replace=False)
        pair_rows.append({"pair": f"p{p + 1:02d}", "question_a": a, "question_b": b, "same_speaker_yes_no": ""})

    with open(out_dir / "answer_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet_rows[0]))
        w.writeheader()
        w.writerows(sheet_rows)
    with open(out_dir / "pair_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pair_rows[0]))
        w.writeheader()
        w.writerows(pair_rows)
    with open(out_dir / "answer_key.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0]))
        w.writeheader()
        w.writerows(key_rows)
    print(f"Listening test with {len(key_rows)} clips and {len(pair_rows)} pairs written to {out_dir}")
    print("Give listeners: audio/, answer_sheet.csv, pair_sheet.csv.  Keep answer_key.csv hidden.")


def score(sheet_path: Path, key_path: Path, pair_path: Path | None) -> None:
    key = {r["question"]: r for r in csv.DictReader(open(key_path, encoding="utf-8-sig"))}
    rows = [r for r in csv.DictReader(open(sheet_path, encoding="utf-8-sig")) if r.get("estimated_age")]
    if not rows:
        print("No filled answers found.")
        return
    true = np.array([float(key[r["question"]]["age"]) for r in rows])
    est = np.array([float(r["estimated_age"]) for r in rows])
    mos = [float(r["naturalness_mos_1_5"]) for r in rows if r.get("naturalness_mos_1_5")]
    corr = float(np.corrcoef(true, est)[0, 1]) if len(rows) > 2 else float("nan")
    print(f"Answers: {len(rows)}")
    print(f"Perceived-age vs label: Pearson r = {corr:.3f}  (target > 0)")
    print(f"Mean absolute age error: {np.mean(np.abs(true - est)):.1f} years; mean bias: {np.mean(est - true):+.1f} years")
    if mos:
        print(f"Naturalness MOS: {np.mean(mos):.2f} ± {np.std(mos):.2f}")
    if pair_path and pair_path.exists():
        pairs = [p for p in csv.DictReader(open(pair_path, encoding="utf-8-sig")) if p.get("same_speaker_yes_no")]
        correct = 0
        for p in pairs:
            same = key[p["question_a"]]["speaker_id"] == key[p["question_b"]]["speaker_id"]
            said = p["same_speaker_yes_no"].strip().lower() in {"yes", "y", "co", "có", "1"}
            correct += int(same == said)
        if pairs:
            print(f"Same/different speaker accuracy: {correct / len(pairs) * 100:.1f}% ({len(pairs)} pairs)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(OUTPUT_DATASET_DIR), help="Dataset directory")
    ap.add_argument("--out", default=str(PROJECT_ROOT / "data" / "listening_test"), help="Output directory")
    ap.add_argument("--per-speaker", type=int, default=3)
    ap.add_argument("--pairs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--score", default=None, help="Filled answer_sheet.csv to score")
    ap.add_argument("--key", default=None, help="answer_key.csv for scoring")
    ap.add_argument("--pairs-sheet", default=None, help="Filled pair_sheet.csv for scoring")
    args = ap.parse_args()

    if args.score:
        key = Path(args.key) if args.key else Path(args.score).parent / "answer_key.csv"
        score(Path(args.score), key, Path(args.pairs_sheet) if args.pairs_sheet else None)
    else:
        build(Path(args.dir), Path(args.out), args.per_speaker, args.pairs, args.seed)


if __name__ == "__main__":
    main()
