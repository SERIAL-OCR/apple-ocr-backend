import argparse
import csv
import json
import os
from typing import Dict, List, Tuple

import requests


def load_labels(labels_path: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with open(labels_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "filename" not in reader.fieldnames or "serial" not in reader.fieldnames:
            raise ValueError("labels.csv must contain 'filename' and 'serial' columns")
        for row in reader:
            mapping[row["filename"]] = row["serial"].strip().upper()
    return mapping


def evaluate(dir_path: str, min_conf: float, persist: bool) -> None:
    labels_file = os.path.join(dir_path, "labels.csv")
    labels = load_labels(labels_file)

    total = 0
    hits = 0
    misses = 0
    low_conf: List[Tuple[str, float]] = []

    for root, _, files in os.walk(dir_path):
        for fn in files:
            if not fn.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            total += 1
            full = os.path.join(root, fn)

            with open(full, "rb") as img:
                files_payload = {"image": (fn, img, "image/png")}
                params = {"min_confidence": str(min_conf), "persist": "true" if persist else "false"}
                r = requests.post("http://localhost:8000/process-serial", files=files_payload, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()

            gt = labels.get(fn) or labels.get(os.path.basename(fn))
            found = False
            if data.get("serials"):
                for cand in data["serials"]:
                    serial = cand.get("serial")
                    conf = float(cand.get("confidence", 0))
                    if serial == gt:
                        hits += 1
                        found = True
                        if conf < min_conf:
                            low_conf.append((fn, conf))
                        break
            if not found:
                misses += 1

    acc = (hits / total) * 100 if total else 0
    print(f"Evaluated {total} images | Hits: {hits} | Misses: {misses} | Accuracy: {acc:.2f}%")
    if low_conf:
        print("Low-confidence correct matches (below threshold):")
        for fn, conf in low_conf[:20]:
            print(f"  {fn}: {conf:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate OCR accuracy against labels.csv")
    parser.add_argument("--dir", required=True, help="Directory containing images and labels.csv")
    parser.add_argument("--min-conf", type=float, default=0.2, help="Minimum confidence threshold")
    parser.add_argument("--persist", action="store_true", help="Persist results to DB")
    args = parser.parse_args()

    evaluate(args.dir, args.min_conf, args.persist)
