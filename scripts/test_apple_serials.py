import os
import sys
import csv
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
import re

# Configuration
API_URL = "http://localhost:8000/process-serial"
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/apple_serials_results.csv"
DEBUG_DIR = "exports/debug/apple_serials"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Test parameters for MacBook etched serials
PARAMS = {
    "min_confidence": 0.0,  # We'll filter later
    "debug_save": True,
    "persist": False,
    "preset": "etched",  # Use etched preset for MacBook bottom cases
    "upscale_scale": 5.0,  # Higher upscaling for small text
    "mode": "gray",
    "roi": False,  # Disable ROI to scan full image
    "glare_reduction": "division",  # Better for metallic surfaces
    "fine_rotation": True,  # Enable fine-grained rotation angles
    "rotations": "0,90,180,270",  # Standard rotations
    "mag_ratio": 1.5,  # Higher magnification ratio
    "low_text": 0.15,  # Lower threshold for faint etched text
    "text_threshold": 0.35,  # Lower threshold for better detection
}

# Regex pattern for Apple serial numbers
APPLE_SERIAL_PATTERN = re.compile(r'[A-Z0-9]{12}')

def preprocess_locally(image_path: str, debug_path: Optional[str] = None):
    """Apply local preprocessing to enhance serial number visibility."""
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error reading image: {image_path}")
        return None
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Apply bilateral filter to smooth while preserving edges
    filtered = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Sharpen the image
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(filtered, -1, kernel)
    
    # Save debug image if requested
    if debug_path:
        cv2.imwrite(debug_path, sharpened)
    
    return sharpened

def extract_text_with_tesseract(image):
    """Extract text using Tesseract OCR as a fallback."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Tesseract error: {e}")
        return ""

def find_serial_in_text(text: str) -> Optional[str]:
    """Find Apple serial number pattern in text."""
    # Look for "Serial" keyword followed by alphanumeric characters
    serial_match = re.search(r'Serial\s+([A-Z0-9]{12})', text, re.IGNORECASE)
    if serial_match:
        return serial_match.group(1)
    
    # Look for any 12-character alphanumeric string that matches Apple pattern
    matches = APPLE_SERIAL_PATTERN.findall(text)
    if matches:
        return matches[0]
    
    return None

def process_image(image_path: str) -> Tuple[bool, float, Optional[str]]:
    """Process a single image through the OCR API."""
    # Create debug path for this image
    base_name = os.path.basename(image_path)
    debug_image_path = os.path.join(DEBUG_DIR, f"preproc_{base_name}")
    
    # Apply local preprocessing
    preprocessed = preprocess_locally(image_path, debug_image_path)
    if preprocessed is None:
        return False, 0.0, None
    
    try:
        # Prepare the file for upload
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
            
            # Send the request
            response = requests.post(
                API_URL,
                files=files,
                params=PARAMS,
                timeout=120  # Longer timeout for fine-grained rotations
            )
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Error processing {image_path}: {response.status_code} - {response.text}")
                return False, 0.0, None
            
            # Parse the response
            result = response.json()
            
            # Check if any serials were detected
            if not result.get("serials"):
                print(f"No serials found in {image_path}")
                
                # Try fallback with Tesseract
                try:
                    import pytesseract
                    print("Trying Tesseract fallback...")
                    text = extract_text_with_tesseract(preprocessed)
                    serial = find_serial_in_text(text)
                    if serial:
                        print(f"Tesseract found serial: {serial} in {image_path}")
                        return True, 0.5, serial  # Assign medium confidence
                except ImportError:
                    print("Tesseract not available for fallback")
                
                return False, 0.0, None
            
            # Get the top result
            top_serial = result["serials"][0]
            print(f"Found serial: {top_serial['serial']} with confidence {top_serial['confidence']:.2f} in {image_path}")
            return True, top_serial["confidence"], top_serial["serial"]
            
    except Exception as e:
        print(f"Exception processing {image_path}: {e}")
        return False, 0.0, None

def main():
    # Get all image files
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Process each image
    results = []
    success_count = 0
    
    for img_file in image_files:
        img_path = os.path.join(IMAGE_DIR, img_file)
        print(f"Processing {img_path}...")
        
        success, confidence, serial = process_image(img_path)
        
        results.append({
            "filename": img_file,
            "success": success,
            "confidence": confidence,
            "detected_serial": serial
        })
        
        if success:
            success_count += 1
    
    # Calculate success rate
    total_images = len(image_files)
    success_rate = (success_count / total_images) * 100 if total_images > 0 else 0
    
    print(f"\nProcessed {total_images} images")
    print(f"Successfully detected serials in {success_count} images ({success_rate:.1f}%)")
    
    # Write results to CSV
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = ['filename', 'success', 'confidence', 'detected_serial']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
