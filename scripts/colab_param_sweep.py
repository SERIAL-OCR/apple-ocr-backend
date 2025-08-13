#!/usr/bin/env python3
"""
Parameter sweep utility for OCR optimization that can be run in Colab.
"""

import argparse
import csv
import json
import os
import sys
import time
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports when running locally
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def load_labels(labels_file: str) -> Dict[str, str]:
    """Load ground truth labels from CSV."""
    labels = {}
    if not os.path.exists(labels_file):
        logger.warning(f"Labels file {labels_file} not found")
        return labels
    
    with open(labels_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'filename' in row and 'serial' in row and row['serial']:
                labels[row['filename']] = row['serial'].strip().upper()
    
    logger.info(f"Loaded {len(labels)} labels from {labels_file}")
    return labels


def process_image(
    image_path: str,
    params: Dict[str, Any],
    true_serial: Optional[str] = None,
) -> Tuple[bool, float, Optional[str]]:
    """
    Process a single image with the given parameters.
    
    Args:
        image_path: Path to the image file
        params: OCR parameters
        true_serial: Ground truth serial number (if available)
    
    Returns:
        Tuple of (match, confidence, detected_serial)
    """
    # This function would normally call the API, but for Colab we'll implement the OCR directly
    try:
        # Import here to avoid errors when the script is first uploaded to Colab
        import cv2
        import numpy as np
        
        # Import our OCR adapter
        from app.pipeline.ocr_adapter_improved import extract_serials
        
        # Read image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Process image
        serials = extract_serials(image_bytes, **params)
        
        if not serials:
            return False, 0.0, None
        
        # Get top serial
        top_serial, confidence = serials[0]
        
        # Check if it matches ground truth
        match = False
        if true_serial:
            match = top_serial.upper() == true_serial.upper()
        
        return match, confidence, top_serial
    
    except Exception as e:
        logger.error(f"Error processing {image_path}: {e}")
        return False, 0.0, None


def run_sweep(
    images_dir: str,
    labels_file: str,
    output_file: str,
    param_grid: Dict[str, List[Any]],
    timeout_s: int = 60,
):
    """Run parameter sweep across all images and parameter combinations."""
    
    # Load labels
    labels = load_labels(labels_file)
    
    # Get all image files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(Path(images_dir).glob(ext))
    
    if not image_files:
        logger.error(f"No images found in {images_dir}")
        return
    
    logger.info(f"Found {len(image_files)} images")
    
    # Generate parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"Testing {len(combinations)} parameter combinations")
    
    results = []
    best_params = None
    best_accuracy = 0
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        logger.info(f"\nTesting combination {i+1}/{len(combinations)}: {params}")
        
        correct = 0
        total = 0
        total_confidence = 0
        
        for image_path in image_files:
            filename = image_path.name
            true_serial = labels.get(filename)
            
            match, confidence, detected = process_image(
                str(image_path), params, true_serial
            )
            
            if match:
                correct += 1
            if detected:  # Only count confidence if something was detected
                total_confidence += confidence
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        detected_count = sum(1 for _, conf, _ in [process_image(str(p), params) for p in image_files] if conf > 0)
        avg_confidence = total_confidence / detected_count if detected_count > 0 else 0
        
        result = {
            **params,
            'accuracy': accuracy,
            'detected': detected_count,
            'total': total,
            'avg_confidence': avg_confidence
        }
        results.append(result)
        
        logger.info(f"  Accuracy: {accuracy:.2%} ({correct}/{total})")
        logger.info(f"  Detection rate: {detected_count/total:.2%} ({detected_count}/{total})")
        logger.info(f"  Avg confidence: {avg_confidence:.3f}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_params = params
    
    # Save results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='') as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Sweep complete! Results saved to {output_file}")
    logger.info(f"\nBest parameters (accuracy: {best_accuracy:.2%}):")
    for k, v in best_params.items():
        logger.info(f"  {k}: {v}")
    
    # Also save best params as JSON for easy loading
    best_params_file = output_file.replace('.csv', '_best.json')
    with open(best_params_file, 'w') as f:
        json.dump({
            'params': best_params,
            'accuracy': best_accuracy
        }, f, indent=2)
    logger.info(f"\nBest parameters saved to {best_params_file}")


def main():
    parser = argparse.ArgumentParser(description='Parameter sweep for OCR tuning')
    parser.add_argument('--images', default='exported-assets', help='Directory containing test images')
    parser.add_argument('--labels', default='exported-assets/labels.csv', help='CSV file with ground truth')
    parser.add_argument('--output', default='exports/param_sweep_results.csv', help='Output CSV file')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout seconds per image')
    parser.add_argument('--rotations', default='0,180', help="Angles to try (e.g. '0,180' or '0,90,180,270')")
    
    # Define parameter ranges to test
    parser.add_argument('--upscale', nargs='+', type=float, default=[3.0, 4.0, 5.0],
                        help='Upscale factors to test')
    parser.add_argument('--modes', nargs='+', default=['gray', 'binary'],
                        help='Processing modes to test')
    parser.add_argument('--low-text', nargs='+', type=float, default=[0.15, 0.2, 0.25],
                        help='EasyOCR low_text values to test')
    parser.add_argument('--text-threshold', nargs='+', type=float, default=[0.35, 0.4, 0.45],
                        help='EasyOCR text_threshold values to test')
    parser.add_argument('--roi-pad', nargs='+', type=int, default=[8, 10, 12, 15],
                        help='ROI padding values to test')
    parser.add_argument('--glare-reduction', nargs='+', default=['tophat', 'division', 'adaptive', None],
                        help='Glare reduction methods to test')
    parser.add_argument('--sharpen', nargs='+', type=bool, default=[True, False],
                        help='Whether to apply sharpening')
    parser.add_argument('--quick', action='store_true',
                        help='Quick test with fewer parameter combinations')
    
    args = parser.parse_args()
    
    # Build parameter grid
    if args.quick:
        # Quick test with fewer combinations
        param_grid = {
            'upscale_scale': [4.0],
            'mode': ['gray'],
            'low_text': [0.15],
            'text_threshold': [0.35],
            'roi': [True],
            'roi_top_k': [3],
            'roi_pad': [12],
            'adaptive_pad': [True],
            'glare_reduction': ['adaptive'],
            'try_rotations': [args.rotations],
            'sharpen': [True],
            'mag_ratio': [1.0],
            'min_confidence': [0.0],
        }
    else:
        # Full parameter sweep
        param_grid = {
            'upscale_scale': args.upscale,
            'mode': args.modes,
            'low_text': args.low_text,
            'text_threshold': args.text_threshold,
            'roi': [True],  # Always use ROI
            'roi_top_k': [2, 3],
            'roi_pad': args.roi_pad,
            'adaptive_pad': [True, False],
            'glare_reduction': args.glare_reduction,
            'try_rotations': [args.rotations],
            'sharpen': args.sharpen,
            'mag_ratio': [1.0, 1.5],
            'min_confidence': [0.0],
        }
    
    # Run the sweep
    run_sweep(
        args.images,
        args.labels,
        args.output,
        param_grid,
        args.timeout,
    )


if __name__ == '__main__':
    main()
