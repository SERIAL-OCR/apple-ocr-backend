"""
Direct testing script for Apple serial OCR without using the API.

This script is based on test_real_images.py but uses the OCR engine directly
instead of going through the API.

Usage:
    python scripts/test_real_images_direct.py
"""

import os
import sys
import csv
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.ocr_adapter_improved import extract_serials
from app.utils.validation import is_valid_apple_serial

# Configuration
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/real_images_direct_results.csv"
DEBUG_DIR = "exports/debug/real_images_direct"

# Create directories
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Simplified parameters for more reliable processing
PARAMS = {
    "min_confidence": 0.0,  # We'll filter later
    "upscale_scale": 3.0,  # Reduced to avoid memory issues
    "mode": "gray",
    "roi": False,  # Disable ROI to scan full image
    "glare_reduction": None,  # Disable to avoid errors
    "fine_rotation": False,  # Disable to avoid errors
    "try_rotations": [0, 180],  # Only try upright and upside down
    "early_stop_confidence": 0.8,  # Stop early if we find a good match
}


def process_image(image_path: str) -> Tuple[bool, float, Optional[str], float]:
    """Process a single image through the OCR engine directly."""
    # Create debug paths for this image
    base_name = os.path.basename(image_path)
    name_without_ext = os.path.splitext(base_name)[0]
    debug_ocr_path = os.path.join(DEBUG_DIR, f"{name_without_ext}")
    
    try:
        # Start timer
        start_time = time.time()
        
        # Read the image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        # Try with our OCR adapter first
        try:
            results = extract_serials(
                image_bytes=image_bytes,
                debug_save_path=debug_ocr_path,
                **PARAMS
            )
        except Exception as e:
            print(f"OCR adapter error: {e}")
            
            # Try with more basic parameters
            try:
                print("Trying with basic parameters...")
                results = extract_serials(
                    image_bytes=image_bytes,
                    debug_save_path=debug_ocr_path + "_basic",
                    min_confidence=0.0,
                    mode="gray",
                    upscale_scale=3.0,
                    roi=False,
                    glare_reduction=None,
                    fine_rotation=False,
                    try_rotations=[0, 180]
                )
            except Exception as e2:
                print(f"Basic OCR also failed: {e2}")
                results = []
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Check if any serials were detected
        if not results:
            print(f"No serials found in {image_path}")
            return False, 0.0, None, processing_time
        
        # Get the top result
        top_serial, top_confidence = results[0]
        print(f"Found serial: {top_serial} with confidence {top_confidence:.2f} in {image_path}")
        return True, top_confidence, top_serial, processing_time
        
    except Exception as e:
        print(f"Exception processing {image_path}: {e}")
        return False, 0.0, None, 0.0


def main():
    # Get all image files
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Process each image
    results = []
    success_count = 0
    total_time = 0.0
    
    for img_file in image_files:
        img_path = os.path.join(IMAGE_DIR, img_file)
        print(f"\nProcessing {img_path}...")
        
        success, confidence, serial, processing_time = process_image(img_path)
        total_time += processing_time
        
        results.append({
            "filename": img_file,
            "success": success,
            "confidence": confidence,
            "detected_serial": serial,
            "processing_time": processing_time
        })
        
        if success:
            success_count += 1
    
    # Calculate statistics
    total_images = len(image_files)
    success_rate = (success_count / total_images) * 100 if total_images > 0 else 0
    avg_time = total_time / total_images if total_images > 0 else 0
    
    print(f"\nProcessed {total_images} images")
    print(f"Successfully detected serials in {success_count} images ({success_rate:.1f}%)")
    print(f"Average processing time: {avg_time:.2f} seconds per image")
    print(f"Total processing time: {total_time:.2f} seconds")
    
    # Write results to CSV
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = ['filename', 'success', 'confidence', 'detected_serial', 'processing_time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
