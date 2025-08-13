from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2

from app.pipeline.ocr_adapter import extract_serials


def _safe_join(base_dir: str, sub_path: str) -> str:
    base_abs = os.path.abspath(base_dir)
    target_abs = os.path.abspath(os.path.join(base_abs, sub_path))
    if not target_abs.startswith(base_abs):
        raise ValueError("Unsafe path")
    return target_abs


def _load_labels(dir_path: str) -> Dict[str, str]:
    labels_path = os.path.join(dir_path, "labels.csv")
    mapping: Dict[str, str] = {}
    if not os.path.exists(labels_path):
        return mapping
    with open(labels_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "filename" not in reader.fieldnames or "serial" not in reader.fieldnames:
            return mapping
        for row in reader:
            fn = (row.get("filename") or "").strip()
            gt = (row.get("serial") or "").strip().upper()
            if fn and gt:
                mapping[fn] = gt
    return mapping


def evaluate_dataset(
    dataset_dir: str,
    min_confidence: float = 0.0,
    persist: bool = False,
    extract_params: Optional[Dict] = None,
) -> Dict:
    """
    Evaluate OCR accuracy for all images under a directory with optional labels.csv.

    Returns a summary dict and writes detailed CSV and summary JSON under exports/reports.
    """
    extract_params = dict(extract_params or {})

    if not os.path.isdir(dataset_dir):
        raise FileNotFoundError(f"Directory not found: {dataset_dir}")

    labels = _load_labels(dataset_dir)

    image_exts = {".png", ".jpg", ".jpeg", ".heic", ".heif"}
    files: List[str] = []
    for root, _, fns in os.walk(dataset_dir):
        for fn in fns:
            if os.path.splitext(fn)[1].lower() in image_exts:
                files.append(os.path.join(root, fn))

    total = len(files)
    detected = 0
    hits = 0

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join("exports", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    csv_path = os.path.join(reports_dir, f"eval_{os.path.basename(os.path.normpath(dataset_dir))}_{ts}.csv")
    json_path = os.path.join(reports_dir, f"eval_{os.path.basename(os.path.normpath(dataset_dir))}_{ts}.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "ground_truth", "top_serial", "top_confidence", "num_candidates", "match", "all_candidates"])  # header

        for full in files:
            rel = os.path.relpath(full, dataset_dir)
            with open(full, "rb") as img_f:
                data = img_f.read()
            try:
                results = extract_serials(
                    data,
                    min_confidence=min_confidence,
                    **extract_params,
                )
            except Exception as exc:  # noqa: BLE001
                writer.writerow([rel, labels.get(os.path.basename(rel), ""), "", "", 0, False, f"ERROR:{exc}"])
                continue

            cands = results or []
            if cands:
                detected += 1
                top_serial, top_conf = cands[0]
                all_flat = ";".join([f"{s}@{float(c):.3f}" for s, c in cands])
            else:
                top_serial, top_conf, all_flat = "", "", ""

            gt = labels.get(os.path.basename(rel)) or labels.get(rel)
            match = bool(gt and cands and any(s == gt for s, _ in cands))
            if match:
                hits += 1

            writer.writerow([rel, gt or "", top_serial, f"{float(top_conf) if top_conf != '' else 0.0:.4f}", len(cands), match, all_flat])

    det_rate = (detected / total * 100.0) if total else 0.0
    acc = (hits / total * 100.0) if total else 0.0
    acc_on_detected = (hits / detected * 100.0) if detected else 0.0

    summary = {
        "dataset": dataset_dir,
        "total": total,
        "detected": detected,
        "hits": hits,
        "detection_rate_pct": round(det_rate, 2),
        "accuracy_pct_overall": round(acc, 2),
        "accuracy_pct_on_detected": round(acc_on_detected, 2),
        "csv_path": csv_path,
        "summary_path": json_path,
    }

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(summary, jf, indent=2)

    return summary


