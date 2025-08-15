"""
Direct testing script for Apple serial OCR without using the API.

This script tests the OCR engine directly on Apple serial images,
bypassing the API to avoid network issues and provide better error handling.

Usage:
    python scripts/test_apple_serials_direct.py
"""

import os
import sys
import csv
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.ocr_adapter_improved import extract_serials
from app.utils.validation import is_valid_apple_serial

# Configuration
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/apple_serials_direct_results.csv"
DEBUG_DIR = "exports/debug/apple_serials_direct"

# Create directories
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Test parameters for MacBook etched serials - using very basic settings
PARAMS = {
    "min_confidence": 0.0,  # We'll filter later
    "upscale_scale": 3.0,  # Moderate upscaling
    "mode": "gray",
    "roi": False,  # Disable ROI to scan full image
    "glare_reduction": None,  # Disable glare reduction to avoid errors
    "fine_rotation": False,  # Disable fine-grained rotation to avoid errors
    "smart_rotation": False,  # Disable smart rotation to avoid errors
    "try_rotations": [0, 180],  # Only try upright and upside down
    "mag_ratio": 1.0,  # Standard magnification
    "low_text": 0.3,  # Default threshold
    "text_threshold": 0.6,  # Default threshold
}

# Regex pattern for Apple serial numbers
APPLE_SERIAL_PATTERN = re.compile(r'[A-Z0-9]{12}')


def preprocess_locally(image_path: str, debug_path: Optional[str] = None):
    """Apply minimal preprocessing to avoid errors."""
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error reading image: {image_path}")
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Simple contrast enhancement
        alpha = 1.3  # Contrast control
        beta = 10    # Brightness control
        enhanced = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
        
        # Save debug image if requested
        if debug_path:
            cv2.imwrite(debug_path, enhanced)
        
        return enhanced
    except Exception as e:
        print(f"Error in preprocessing: {str(e)}")
        return None


def process_image(image_path: str) -> Tuple[bool, float, Optional[str], float]:
    """Process a single image through the OCR engine directly."""
    # Create debug paths for this image
    base_name = os.path.basename(image_path)
    name_without_ext = os.path.splitext(base_name)[0]
    debug_image_path = os.path.join(DEBUG_DIR, f"preproc_{base_name}")
    debug_ocr_path = os.path.join(DEBUG_DIR, f"ocr_{name_without_ext}")
    
    try:
        # Start timer
        start_time = time.time()
        
        # Apply local preprocessing
        preprocessed = preprocess_locally(image_path, debug_image_path)
        if preprocessed is None:
            return False, 0.0, None, 0.0
            
        # Try direct approach with EasyOCR
        try:
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False)  # Force CPU mode
            print("Using EasyOCR directly...")
            
            # Run OCR
            results = reader.readtext(
                preprocessed,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                low_text=0.3,
                text_threshold=0.6,
                mag_ratio=1.0,
            )
            
            # Process results
            serials = []
            for bbox, text, confidence in results:
                # Clean up text
                clean_text = text.strip().upper().replace(" ", "")
                
                # Check if it's a valid serial
                if len(clean_text) == 12 and is_valid_apple_serial(clean_text):
                    serials.append((clean_text, float(confidence)))
            
            # Sort by confidence
            serials.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            print(f"EasyOCR error: {e}")
            serials = []
            
        # If direct approach failed, try with our adapter
        if not serials:
            # Convert preprocessed image to bytes
            _, img_bytes = cv2.imencode(".png", preprocessed)
            image_bytes = img_bytes.tobytes()
            
            # Process with OCR adapter
            try:
                serials = extract_serials(
                    image_bytes=image_bytes,
                    debug_save_path=debug_ocr_path,
                    **PARAMS
                )
            except Exception as e:
                print(f"OCR adapter error: {e}")
                serials = []
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Check if any serials were detected
        if not serials:
            print(f"No serials found in {image_path}")
            return False, 0.0, None, processing_time
        
        # Get the top result
        top_serial, top_confidence = serials[0]
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
