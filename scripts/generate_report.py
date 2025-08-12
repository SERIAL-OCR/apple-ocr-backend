import argparse
import csv
import os
import mimetypes
from typing import Dict, List, Optional, Tuple

import requests


def load_labels(labels_path: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    try:
        with open(labels_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if "filename" not in reader.fieldnames or "serial" not in reader.fieldnames:
                return mapping
            for row in reader:
                mapping[row["filename"]] = row["serial"].strip().upper()
    except FileNotFoundError:
        pass
    return mapping


def generate_report(
    dir_path: str,
    min_conf: float,
    extra_query: str,
    out_csv: str,
    persist: bool,
) -> None:
    labels = load_labels(os.path.join(dir_path, "labels.csv"))

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    total = 0
    detected = 0
    hits = 0

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "top_serial", "top_confidence", "num_candidates", "all_candidates"])  # header

        for root, _, files in os.walk(dir_path):
            for fn in files:
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".heif")):
                    continue
                total += 1
                full = os.path.join(root, fn)

                with open(full, "rb") as img:
                    mime, _ = mimetypes.guess_type(full)
                    if mime is None:
                        # Default to jpeg to satisfy server allowlist
                        if fn.lower().endswith((".png",)):
                            mime = "image/png"
                        elif fn.lower().endswith((".heic", ".heif")):
                            mime = "image/heic"
                        else:
                            mime = "image/jpeg"
                    files_payload = {"image": (fn, img, mime)}
                    params = {"min_confidence": str(min_conf), "persist": "true" if persist else "false"}
                    if extra_query:
                        for part in extra_query.split("&"):
                            if not part:
                                continue
                            if "=" in part:
                                k, v = part.split("=", 1)
                                params[k] = v
                    r = requests.post("http://localhost:8000/process-serial", files=files_payload, params=params, timeout=60)
                    r.raise_for_status()
                    data = r.json()

                cands = data.get("serials") or []
                if cands:
                    detected += 1
                    top = max(cands, key=lambda x: float(x.get("confidence", 0.0)))
                    top_serial = top.get("serial")
                    top_conf = float(top.get("confidence", 0.0))
                    all_flat = ";".join([f"{c.get('serial')}@{float(c.get('confidence',0.0)):.3f}" for c in cands])
                    writer.writerow([fn, top_serial, f"{top_conf:.4f}", len(cands), all_flat])
                    gt = labels.get(fn) or labels.get(os.path.basename(fn))
                    if gt and any(c.get("serial") == gt for c in cands):
                        hits += 1
                else:
                    writer.writerow([fn, "", "", 0, ""])

    print(f"Images: {total} | Detected: {detected} | Det. Rate: {(detected/total*100 if total else 0):.2f}%")
    if labels:
        print(f"Exact matches vs labels.csv: {hits}/{total} ({(hits/total*100 if total else 0):.2f}%)")
    print(f"Report written to: {out_csv}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate OCR report for a directory of images")
    p.add_argument("--dir", required=True, help="Directory containing images (and optional labels.csv)")
    p.add_argument("--min-conf", type=float, default=0.1, help="Minimum confidence threshold")
    p.add_argument("--extra", default="", help="Extra query string parameters for API (e.g., mode=gray&upscale_scale=3.0)")
    p.add_argument("--out-csv", required=True, help="Path to write CSV report")
    p.add_argument("--persist", action="store_true", help="Persist results to DB")
    args = p.parse_args()

    generate_report(args.dir, args.min_conf, args.extra, args.out_csv, args.persist)
