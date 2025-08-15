"""
Memory-efficient testing script for Apple serial OCR.

This script uses minimal memory settings to avoid CUDA out of memory errors.

Usage:
    python scripts/test_memory_efficient.py
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
OUTPUT_CSV = "reports/memory_efficient_results.csv"
DEBUG_DIR = "exports/debug/memory_efficient"

# Create directories
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Memory-efficient parameters
PARAMS = {
    "min_confidence": 0.0,
    "upscale_scale": 2.0,  # Lower upscale to save memory
    "mode": "gray",
    "roi": False,
    "glare_reduction": None,  # Disable to save memory
    "fine_rotation": False,
    "try_rotations": [0, 180],  # Only two rotations to save processing time
    "early_stop_confidence": 0.8,
}

# Force CPU mode to avoid CUDA memory issues
os.environ["FORCE_CPU"] = "1"

def preprocess_image(image_path: str) -> np.ndarray:
    """Apply basic preprocessing to enhance serial number visibility."""
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error reading image: {image_path}")
            return None
        
        # Resize large images to save memory
        h, w = img.shape[:2]
        if max(h, w) > 1024:
            scale = 1024 / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            print(f"Resized image from {w}x{h} to {new_w}x{new_h} to save memory")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Simple contrast enhancement
        alpha = 1.3  # Contrast control
        beta = 10    # Brightness control
        enhanced = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
        
        return enhanced
    except Exception as e:
        print(f"Error in preprocessing: {str(e)}")
        return None

def process_image(image_path: str) -> Tuple[bool, float, Optional[str], float]:
    """Process a single image with memory-efficient settings."""
    # Create debug path for this image
    base_name = os.path.basename(image_path)
    name_without_ext = os.path.splitext(base_name)[0]
    debug_path = os.path.join(DEBUG_DIR, f"{name_without_ext}")
    
    try:
        # Start timer
        start_time = time.time()
        
        # Preprocess image
        preprocessed = preprocess_image(image_path)
        if preprocessed is None:
            return False, 0.0, None, 0.0
        
        # Convert to bytes
        _, img_bytes = cv2.imencode(".png", preprocessed)
        image_bytes = img_bytes.tobytes()
        
        # Process with OCR
        results = extract_serials(
            image_bytes=image_bytes,
            debug_save_path=debug_path,
            **PARAMS
        )
        
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
