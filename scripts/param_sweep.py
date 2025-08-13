#!/usr/bin/env python3
"""
Parameter sweep utility for finding optimal OCR settings.
Tests different parameter combinations and reports accuracy.
"""

import argparse
import csv
import json
import os
import sys
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

import requests


def load_labels(labels_file: str) -> Dict[str, str]:
    """Load ground truth labels from CSV."""
    labels = {}
    if not os.path.exists(labels_file):
        print(f"Warning: Labels file {labels_file} not found")
        return labels
    
    with open(labels_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            labels[row['filename']] = row['serial']
    return labels


def test_parameters(
    api_url: str,
    image_path: str,
    params: Dict[str, any],
    true_serial: str = None,
    timeout_s: int = 45,
) -> Tuple[bool, float, str]:
    """Test a single image with given parameters."""
    url = f"{api_url}/process-serial"
    
    # Add persist=false to avoid saving test data
    params['persist'] = 'false'
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f, 'image/png')}
            response = requests.post(url, files=files, params=params, timeout=timeout_s)
        
        if response.status_code != 200:
            return False, 0.0, None
        
        data = response.json()
        if not data.get('serials'):
            return False, 0.0, None
        
        top_serial = data['serials'][0]['serial']
        confidence = data['serials'][0]['confidence']
        
        if true_serial:
            # Check if detected serial matches ground truth
            detected = top_serial.replace(' ', '').upper()
            expected = true_serial.replace(' ', '').upper()
            match = detected == expected
        else:
            # No ground truth, just check if something was detected
            match = True
        
        return match, confidence, top_serial
    
    except Exception as e:
        print(f"Error testing {image_path}: {e}")
        return False, 0.0, None


def run_sweep(
    api_url: str,
    images_dir: str,
    labels_file: str,
    output_file: str,
    param_grid: Dict[str, List[any]],
    timeout_s: int,
):
    """Run parameter sweep across all images and parameter combinations."""
    
    # Load labels
    labels = load_labels(labels_file)
    
    # Get all image files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(Path(images_dir).glob(ext))
    
    if not image_files:
        print(f"No images found in {images_dir}")
        return
    
    print(f"Found {len(image_files)} images")
    
    # Generate parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"Testing {len(combinations)} parameter combinations")
    
    results = []
    best_params = None
    best_accuracy = 0
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        print(f"\nTesting combination {i+1}/{len(combinations)}: {params}")
        
        correct = 0
        total = 0
        total_confidence = 0
        
        for image_path in image_files:
            filename = image_path.name
            true_serial = labels.get(filename)
            
            match, confidence, detected = test_parameters(
                api_url, str(image_path), params, true_serial, timeout_s=timeout_s
            )
            
            if match:
                correct += 1
            total += 1
            total_confidence += confidence
        
        accuracy = correct / total if total > 0 else 0
        avg_confidence = total_confidence / total if total > 0 else 0
        
        result = {
            **params,
            'accuracy': accuracy,
            'detected': correct,
            'total': total,
            'avg_confidence': avg_confidence
        }
        results.append(result)
        
        print(f"  Accuracy: {accuracy:.2%} ({correct}/{total})")
        print(f"  Avg confidence: {avg_confidence:.3f}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_params = params
    
    # Save results
    with open(output_file, 'w', newline='') as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    print(f"\n{'='*60}")
    print(f"Sweep complete! Results saved to {output_file}")
    print(f"\nBest parameters (accuracy: {best_accuracy:.2%}):")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    
    # Also save best params as JSON for easy loading
    best_params_file = output_file.replace('.csv', '_best.json')
    with open(best_params_file, 'w') as f:
        json.dump({
            'params': best_params,
            'accuracy': best_accuracy
        }, f, indent=2)
    print(f"\nBest parameters saved to {best_params_file}")


def main():
    parser = argparse.ArgumentParser(description='Parameter sweep for OCR tuning')
    parser.add_argument('--api-url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--images', default='exported-assets', help='Directory containing test images')
    parser.add_argument('--labels', default='exported-assets/labels.csv', help='CSV file with ground truth')
    parser.add_argument('--output', default='exports/param_sweep_results.csv', help='Output CSV file')
    parser.add_argument('--timeout', type=int, default=45, help='HTTP timeout seconds per image')
    parser.add_argument('--rotations', default='0,180', help="Angles to try to speed up API (e.g. '0,180' or '0,90,180,270')")
    
    # Define parameter ranges to test
    parser.add_argument('--upscale', nargs='+', type=float, default=[2.0, 3.0, 4.0],
                        help='Upscale factors to test')
    parser.add_argument('--modes', nargs='+', default=['gray', 'binary'],
                        help='Processing modes to test')
    parser.add_argument('--low-text', nargs='+', type=float, default=[0.15, 0.2, 0.25, 0.3],
                        help='EasyOCR low_text values to test')
    parser.add_argument('--text-threshold', nargs='+', type=float, default=[0.35, 0.4, 0.45, 0.5],
                        help='EasyOCR text_threshold values to test')
    parser.add_argument('--roi-pad', nargs='+', type=int, default=[8, 10, 12, 15],
                        help='ROI padding values to test')
    parser.add_argument('--quick', action='store_true',
                        help='Quick test with fewer parameter combinations')
    
    args = parser.parse_args()
    
    # Build parameter grid
    if args.quick:
        # Quick test with fewer combinations
        param_grid = {
            'upscale_scale': [3.0, 4.0],
            'mode': ['gray'],
            'low_text': [0.2],
            'text_threshold': [0.4],
            'roi': [True],
            'roi_pad': [10],
            'rotations': [args.rotations],
        }
    else:
        # Full parameter sweep
        param_grid = {
            'upscale_scale': args.upscale,
            'mode': args.modes,
            'low_text': args.low_text,
            'text_threshold': args.text_threshold,
            'roi': [True],  # Always use ROI
            'roi_pad': args.roi_pad,
            'rotations': [args.rotations],
        }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Run the sweep
    run_sweep(
        args.api_url,
        args.images,
        args.labels,
        args.output,
        param_grid,
        args.timeout,
    )


if __name__ == '__main__':
    main()
