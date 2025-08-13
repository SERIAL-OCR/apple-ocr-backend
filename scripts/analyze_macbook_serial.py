import os
import sys
import csv
import cv2
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional
import re

# Configuration
IMAGE_PATH = "Apple serial/IMG-20250813-WA0039.jpg"
KNOWN_SERIAL = "C02Y95A8JG5H"
DEBUG_DIR = "exports/debug/macbook_serial"
API_URL = "http://localhost:8000/process-serial"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)

def preprocess_for_macbook_serial(image_path: str) -> List[np.ndarray]:
    """Apply specialized preprocessing for MacBook etched serials."""
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error reading image: {image_path}")
        return []
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Save original grayscale
    cv2.imwrite(os.path.join(DEBUG_DIR, "01_gray.png"), gray)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    cv2.imwrite(os.path.join(DEBUG_DIR, "02_clahe.png"), enhanced)
    
    # Apply bilateral filter to smooth while preserving edges
    filtered = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    cv2.imwrite(os.path.join(DEBUG_DIR, "03_bilateral.png"), filtered)
    
    # Background division (good for metallic surfaces)
    background = cv2.GaussianBlur(filtered, (51, 51), 0)
    divided = cv2.divide(filtered, background, scale=255)
    cv2.imwrite(os.path.join(DEBUG_DIR, "04_divided.png"), divided)
    
    # Sharpen the image
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(filtered, -1, kernel)
    cv2.imwrite(os.path.join(DEBUG_DIR, "05_sharpened.png"), sharpened)
    
    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 45, 9
    )
    cv2.imwrite(os.path.join(DEBUG_DIR, "06_threshold.png"), thresh)
    
    # Upscale for better OCR
    scale = 4.0
    upscaled = cv2.resize(filtered, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(DEBUG_DIR, "07_upscaled.png"), upscaled)
    
    # Return multiple preprocessed versions to try
    return [filtered, divided, sharpened, thresh, upscaled]

def test_api_with_params(image_path: str, params: Dict) -> Tuple[bool, float, Optional[str]]:
    """Test the OCR API with specific parameters."""
    try:
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
            
            response = requests.post(
                API_URL,
                files=files,
                params=params,
                timeout=90
            )
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return False, 0.0, None
            
            result = response.json()
            
            if not result.get("serials"):
                return False, 0.0, None
            
            top_serial = result["serials"][0]
            return True, top_serial["confidence"], top_serial["serial"]
            
    except Exception as e:
        print(f"Exception: {e}")
        return False, 0.0, None

def main():
    print(f"Analyzing image: {IMAGE_PATH}")
    print(f"Known serial number: {KNOWN_SERIAL}")
    
    # Try different parameter combinations
    param_sets = [
        {
            "preset": "etched",
            "upscale_scale": 5.0,
            "mode": "gray",
            "roi": False,
            "glare_reduction": "division",
            "fine_rotation": True,
            "rotations": "0",
            "mag_ratio": 1.5,
            "low_text": 0.15,
            "text_threshold": 0.35,
        },
        {
            "preset": "etched",
            "upscale_scale": 6.0,
            "mode": "gray",
            "roi": False,
            "glare_reduction": "division",
            "fine_rotation": True,
            "rotations": "0",
            "mag_ratio": 2.0,
            "low_text": 0.1,
            "text_threshold": 0.3,
        },
        {
            "preset": "etched",
            "upscale_scale": 4.0,
            "mode": "binary",
            "roi": False,
            "glare_reduction": "division",
            "fine_rotation": True,
            "rotations": "0",
            "mag_ratio": 1.5,
            "low_text": 0.15,
            "text_threshold": 0.35,
        }
    ]
    
    print("\nTesting with different parameter sets:")
    for i, params in enumerate(param_sets):
        print(f"\nParameter set {i+1}:")
        for k, v in params.items():
            print(f"  {k}: {v}")
        
        success, confidence, serial = test_api_with_params(IMAGE_PATH, params)
        
        if success:
            print(f"✓ Detected: {serial} (confidence: {confidence:.2f})")
            if serial == KNOWN_SERIAL:
                print("✓ MATCH with known serial!")
            else:
                print(f"✗ NO MATCH with known serial ({KNOWN_SERIAL})")
        else:
            print("✗ No serial detected")
    
    # Try with local preprocessing
    print("\nTrying with local preprocessing:")
    preprocessed_images = preprocess_for_macbook_serial(IMAGE_PATH)
    
    for i, img in enumerate(preprocessed_images):
        # Save preprocessed image
        temp_path = os.path.join(DEBUG_DIR, f"temp_preproc_{i}.png")
        cv2.imwrite(temp_path, img)
        
        print(f"\nPreprocessed version {i+1}:")
        
        # Use best params
        best_params = {
            "preset": "etched",
            "upscale_scale": 1.0,  # Already upscaled in preprocessing
            "mode": "gray",
            "roi": False,
            "fine_rotation": False,
            "rotations": "0",
            "mag_ratio": 2.0,
            "low_text": 0.1,
            "text_threshold": 0.3,
        }
        
        success, confidence, serial = test_api_with_params(temp_path, best_params)
        
        if success:
            print(f"✓ Detected: {serial} (confidence: {confidence:.2f})")
            if serial == KNOWN_SERIAL:
                print("✓ MATCH with known serial!")
            else:
                print(f"✗ NO MATCH with known serial ({KNOWN_SERIAL})")
        else:
            print("✗ No serial detected")
    
    print("\nAnalysis complete. Check the debug directory for preprocessed images.")

if __name__ == "__main__":
    main()
