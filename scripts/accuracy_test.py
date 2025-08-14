"""
Accuracy test script for the OCR pipeline.

This script evaluates the OCR accuracy against known serial numbers
from a labels.csv file in the image directory.

Usage:
    python scripts/accuracy_test.py --dir "Apple serial" --preset etched-dark
"""

import os
import sys
import argparse
import time
import csv
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.ocr_adapter_improved import extract_serials
from app.config import DEVICE_PRESETS


def load_labels(dir_path: str) -> Dict[str, str]:
    """Load ground truth labels from labels.csv file."""
    labels_path = os.path.join(dir_path, "labels.csv")
    mapping = {}
    
    if not os.path.exists(labels_path):
        print(f"Warning: No labels.csv found in {dir_path}")
        return mapping
    
    with open(labels_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "filename" not in reader.fieldnames or "serial" not in reader.fieldnames:
            print(f"Warning: Invalid format in labels.csv")
            return mapping
        
        for row in reader:
            fn = (row.get("filename") or "").strip()
            gt = (row.get("serial") or "").strip().upper()
            if fn and gt:
                mapping[fn] = gt
    
    print(f"Loaded {len(mapping)} ground truth labels")
    return mapping


def process_image(
    image_path: str,
    preset: Optional[str] = None,
) -> Tuple[List[Tuple[str, float]], float]:
    """Process a single image with the OCR pipeline."""
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return [], 0.0
    
    # Convert to bytes
    _, img_bytes = cv2.imencode(".png", img)
    image_bytes = img_bytes.tobytes()
    
    # Get preset parameters
    extract_params = {}
    if preset and preset in DEVICE_PRESETS:
        extract_params = DEVICE_PRESETS[preset].copy()
    
    # Start timer
    start_time = time.time()
    
    # Use safe parameters to avoid errors
    safe_params = {
        'min_confidence': extract_params.get('min_confidence', 0.0),
        'mode': 'gray',  # Use grayscale mode which is safer
        'upscale_scale': extract_params.get('upscale_scale', 3.0),
        'glare_reduction': extract_params.get('glare_reduction', 'adaptive'),
        'roi': False,  # Disable ROI to avoid errors
        'smart_rotation': True,
        'fine_rotation': False,
        'low_text': extract_params.get('low_text', 0.15),
        'text_threshold': extract_params.get('text_threshold', 0.35),
        'mag_ratio': extract_params.get('mag_ratio', 1.5),
    }
    
    try:
        # Process image
        results = extract_serials(
            image_bytes=image_bytes,
            **safe_params
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return results, processing_time
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return [], time.time() - start_time


def evaluate_accuracy(dir_path: str, preset: Optional[str] = None, limit: Optional[int] = None) -> Dict:
    """Evaluate OCR accuracy on a directory of images."""
    # Load ground truth labels
    labels = load_labels(dir_path)
    
    # Find image files
    image_files = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                image_files.append(os.path.join(root, file))
    
    # Sort image files
    image_files.sort()
    
    # Limit number of images if specified
    if limit is not None and limit > 0:
        image_files = image_files[:limit]
    
    print(f"Found {len(image_files)} images to process")
    
    # Process images and evaluate accuracy
    results = []
    correct_count = 0
    detected_count = 0
    
    for i, image_path in enumerate(image_files):
        filename = os.path.basename(image_path)
        print(f"\nProcessing {i+1}/{len(image_files)}: {filename}")
        
        # Get ground truth serial
        ground_truth = labels.get(filename, "")
        if not ground_truth:
            print(f"No ground truth label for {filename}, skipping")
            continue
        
        # Process image
        ocr_results, processing_time = process_image(image_path, preset)
        
        # Check if any result matches ground truth
        is_correct = False
        if ocr_results:
            detected_count += 1
            top_result = ocr_results[0][0]
            top_confidence = ocr_results[0][1]
            
            print(f"Ground truth: {ground_truth}")
            print(f"OCR result:   {top_result} (confidence: {top_confidence:.3f})")
            
            if top_result == ground_truth:
                is_correct = True
                correct_count += 1
                print("✓ CORRECT")
            else:
                print("✗ INCORRECT")
        else:
            print(f"Ground truth: {ground_truth}")
            print("No OCR results")
        
        # Store result
        results.append({
            "filename": filename,
            "ground_truth": ground_truth,
            "ocr_results": ocr_results,
            "is_correct": is_correct,
            "processing_time": processing_time,
        })
    
    # Calculate statistics
    total_images = len(results)
    detection_rate = detected_count / total_images if total_images > 0 else 0
    accuracy_overall = correct_count / total_images if total_images > 0 else 0
    accuracy_detected = correct_count / detected_count if detected_count > 0 else 0
    
    print("\n===== ACCURACY SUMMARY =====")
    print(f"Total images processed: {total_images}")
    print(f"Detection rate: {detection_rate:.2%} ({detected_count}/{total_images})")
    print(f"Overall accuracy: {accuracy_overall:.2%} ({correct_count}/{total_images})")
    print(f"Accuracy on detected: {accuracy_detected:.2%} ({correct_count}/{detected_count})")
    
    return {
        "total_images": total_images,
        "detected_count": detected_count,
        "correct_count": correct_count,
        "detection_rate": detection_rate,
        "accuracy_overall": accuracy_overall,
        "accuracy_detected": accuracy_detected,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate OCR accuracy")
    parser.add_argument("--dir", required=True, help="Directory containing images and labels.csv")
    parser.add_argument("--preset", help="Device preset to use")
    parser.add_argument("--limit", type=int, help="Limit number of images to process")
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.dir):
        print(f"Error: Directory not found: {args.dir}")
        return
    
    # Evaluate accuracy
    evaluate_accuracy(args.dir, args.preset, args.limit)


if __name__ == "__main__":
    main()
