from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import cv2

from app.pipeline.ocr_adapter_improved import extract_serials, progressive_process
from app.utils.validation import is_valid_apple_serial, validate_apple_serial_extended


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
    use_progressive: bool = True,
    save_debug_images: bool = False,
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
            # Create debug path if needed
            debug_path = None
            if save_debug_images:
                debug_dir = os.path.join(reports_dir, "debug_images")
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f"{os.path.splitext(os.path.basename(rel))[0]}_debug.png")
            
            try:
                if use_progressive:
                    results = progressive_process(
                        data,
                        min_confidence=min_confidence,
                        debug_save_path=debug_path,
                        max_processing_time=45.0,  # 45 second timeout
                    )
                else:
                    results = extract_serials(
                        data,
                        min_confidence=min_confidence,
                        debug_save_path=debug_path,
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

    # Calculate additional metrics
    strict_validation_passes = 0
    high_confidence_hits = 0
    high_confidence_count = 0
    
    # Re-read the CSV to calculate additional metrics
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("top_serial"):
                # Check strict validation
                is_valid, _ = validate_apple_serial_extended(row.get("top_serial", ""))
                if is_valid:
                    strict_validation_passes += 1
                
                # Check high confidence hits
                try:
                    conf = float(row.get("top_confidence", "0"))
                    if conf >= 0.8:  # High confidence threshold
                        high_confidence_count += 1
                        if row.get("match") == "True":
                            high_confidence_hits += 1
                except ValueError:
                    pass
    
    # Calculate rates
    strict_validation_rate = (strict_validation_passes / total * 100.0) if total else 0.0
    high_conf_accuracy = (high_confidence_hits / high_confidence_count * 100.0) if high_confidence_count else 0.0
    
    summary = {
        "dataset": dataset_dir,
        "total": total,
        "detected": detected,
        "hits": hits,
        "detection_rate_pct": round(det_rate, 2),
        "accuracy_pct_overall": round(acc, 2),
        "accuracy_pct_on_detected": round(acc_on_detected, 2),
        "strict_validation_passes": strict_validation_passes,
        "strict_validation_rate_pct": round(strict_validation_rate, 2),
        "high_confidence_count": high_confidence_count,
        "high_confidence_hits": high_confidence_hits,
        "high_confidence_accuracy_pct": round(high_conf_accuracy, 2),
        "csv_path": csv_path,
        "summary_path": json_path,
        "use_progressive": use_progressive,
        "extract_params": extract_params,
    }

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(summary, jf, indent=2)

    return summary


