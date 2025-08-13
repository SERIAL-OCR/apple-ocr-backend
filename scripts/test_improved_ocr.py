#!/usr/bin/env python3
"""
Test script for improved OCR adapter with detailed diagnostics.
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path
import logging

import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipeline.ocr_adapter_improved import preprocess_image, extract_serials


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_labels(labels_file: str):
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
    output_dir: str,
    params: dict,
    true_serial: str = None,
):
    """Process a single image with the improved OCR adapter."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Generate debug paths
    basename = os.path.basename(image_path)
    name_without_ext = os.path.splitext(basename)[0]
    timestamp = int(time.time() * 1000)
    debug_dir = os.path.join(output_dir, f"{name_without_ext}_{timestamp}")
    os.makedirs(debug_dir, exist_ok=True)
    
    debug_path = os.path.join(debug_dir, "preprocessed.png")
    
    # Process with detailed debugging
    start_time = time.time()
    
    # Extract serials with detailed preprocessing steps
    serials = extract_serials(
        image_bytes,
        debug_save_path=debug_path,
        debug_steps=True,
        **params
    )
    
    processing_time = time.time() - start_time
    
    # Save results
    results = {
        "image": basename,
        "processing_time": processing_time,
        "serials": serials,
        "true_serial": true_serial,
        "match": False,
    }
    
    # Check if any serial matches ground truth
    if true_serial and serials:
        for serial, _ in serials:
            if serial.upper() == true_serial.upper():
                results["match"] = True
                break
    
    # Save detection results
    with open(os.path.join(debug_dir, "results.txt"), 'w') as f:
        f.write(f"Image: {basename}\n")
        f.write(f"Processing time: {processing_time:.3f} seconds\n")
        if true_serial:
            f.write(f"True serial: {true_serial}\n")
        f.write(f"Detected serials:\n")
        for serial, confidence in serials:
            match_indicator = " ✓" if true_serial and serial.upper() == true_serial.upper() else ""
            f.write(f"  {serial} (confidence: {confidence:.3f}){match_indicator}\n")
    
    # Return results
    return results


def main():
    parser = argparse.ArgumentParser(description='Test improved OCR adapter')
    parser.add_argument('--image', required=True, help='Path to image or directory of images')
    parser.add_argument('--labels', default=None, help='Path to labels CSV file')
    parser.add_argument('--output', default='exports/improved_ocr_test', help='Output directory')
    
    # OCR parameters
    parser.add_argument('--upscale', type=float, default=4.0, help='Upscale factor')
    parser.add_argument('--mode', choices=['gray', 'binary'], default='gray', help='Processing mode')
    parser.add_argument('--low-text', type=float, default=0.15, help='EasyOCR low_text value')
    parser.add_argument('--text-threshold', type=float, default=0.35, help='EasyOCR text_threshold value')
    parser.add_argument('--roi', action='store_true', help='Use ROI detection')
    parser.add_argument('--roi-top-k', type=int, default=3, help='Number of ROIs to detect')
    parser.add_argument('--roi-pad', type=int, default=12, help='ROI padding')
    parser.add_argument('--adaptive-pad', action='store_true', help='Use adaptive ROI padding')
    parser.add_argument('--glare-reduction', choices=['tophat', 'division', 'adaptive', 'none'], default='adaptive',
                        help='Glare reduction method')
    parser.add_argument('--rotations', default='0,90,180,270', help='Rotation angles to try')
    parser.add_argument('--sharpen', action='store_true', help='Apply sharpening')
    parser.add_argument('--mag-ratio', type=float, default=1.0, help='EasyOCR magnification ratio')
    
    args = parser.parse_args()
    
    # Process glare_reduction=none as None
    glare_reduction = None if args.glare_reduction == 'none' else args.glare_reduction
    
    # Parse rotations
    rotations = [int(r) for r in args.rotations.split(',')]
    
    # Build parameters
    params = {
        'upscale_scale': args.upscale,
        'mode': args.mode,
        'low_text': args.low_text,
        'text_threshold': args.text_threshold,
        'roi': args.roi,
        'roi_top_k': args.roi_top_k,
        'roi_pad': args.roi_pad,
        'adaptive_pad': args.adaptive_pad,
        'glare_reduction': glare_reduction,
        'try_rotations': rotations,
        'sharpen': args.sharpen,
        'mag_ratio': args.mag_ratio,
        'min_confidence': 0.0,  # No confidence filtering
    }
    
    # Load labels if provided
    labels = {}
    if args.labels:
        labels = load_labels(args.labels)
    
    # Process image(s)
    if os.path.isdir(args.image):
        # Process all images in directory
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_files.extend(Path(args.image).glob(ext))
        
        if not image_files:
            logger.error(f"No images found in {args.image}")
            return
        
        logger.info(f"Processing {len(image_files)} images")
        
        results = []
        for image_path in image_files:
            filename = os.path.basename(image_path)
            true_serial = labels.get(filename)
            
            try:
                result = process_image(
                    str(image_path),
                    args.output,
                    params,
                    true_serial
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
        
        # Summarize results
        total = len(results)
        detected = sum(1 for r in results if r["serials"])
        matches = sum(1 for r in results if r["match"])
        
        logger.info(f"Summary: {detected}/{total} images had detections ({detected/total*100:.1f}%)")
        if labels:
            logger.info(f"Accuracy: {matches}/{total} correct matches ({matches/total*100:.1f}%)")
        
        # Save summary
        with open(os.path.join(args.output, "summary.txt"), 'w') as f:
            f.write(f"Total images: {total}\n")
            f.write(f"Images with detections: {detected} ({detected/total*100:.1f}%)\n")
            if labels:
                f.write(f"Correct matches: {matches} ({matches/total*100:.1f}%)\n")
    else:
        # Process single image
        filename = os.path.basename(args.image)
        true_serial = labels.get(filename)
        
        try:
            result = process_image(
                args.image,
                args.output,
                params,
                true_serial
            )
            
            logger.info(f"Results for {filename}:")
            logger.info(f"  Processing time: {result['processing_time']:.3f} seconds")
            logger.info(f"  Detected serials: {len(result['serials'])}")
            for serial, confidence in result["serials"]:
                logger.info(f"    {serial} (confidence: {confidence:.3f})")
            
            if true_serial:
                logger.info(f"  True serial: {true_serial}")
                logger.info(f"  Match: {result['match']}")
        except Exception as e:
            logger.error(f"Error processing {args.image}: {e}")


if __name__ == '__main__':
    main()
