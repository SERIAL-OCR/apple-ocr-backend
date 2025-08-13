import os
import sys
import cv2
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional
import re

# Configuration
IMAGE_PATH = "Apple serial/IMG-20250813-WA0039.jpg"
KNOWN_SERIAL = "C02Y95A8JG5H"
DEBUG_DIR = "exports/debug/character_optimization"
API_URL = "http://localhost:8000/process-serial"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)

# Character confusion mapping (commonly confused characters in Apple serials)
CHAR_CONFUSION = {
    '6': 'G',  # 6 is often confused with G
    '5': 'S',  # 5 is often confused with S
    '0': 'O',  # 0 is often confused with O
    '1': 'I',  # 1 is often confused with I
    '4': 'A',  # 4 is often confused with A
    '8': 'B',  # 8 is often confused with B
}

def apply_character_corrections(detected: str) -> List[str]:
    """Apply character corrections based on common OCR confusions."""
    variants = [detected]
    
    # Generate all possible variants by replacing commonly confused characters
    for i, char in enumerate(detected):
        if char in CHAR_CONFUSION:
            for variant in list(variants):  # Create a copy to avoid modifying during iteration
                corrected = variant[:i] + CHAR_CONFUSION[char] + variant[i+1:]
                variants.append(corrected)
        elif char in CHAR_CONFUSION.values():
            # Also try the reverse mapping
            reverse_map = {v: k for k, v in CHAR_CONFUSION.items()}
            if char in reverse_map:
                for variant in list(variants):
                    corrected = variant[:i] + reverse_map[char] + variant[i+1:]
                    variants.append(corrected)
    
    return variants

def crop_to_serial_region(image_path: str, debug_path: Optional[str] = None):
    """Crop the image to focus on the serial number region."""
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # For MacBook bottom cases, serial is usually in the middle third of the image
    h, w = img.shape[:2]
    
    # Try different crop regions
    crops = []
    
    # Middle horizontal strip (where most serials are)
    mid_y = h // 2
    top_third = max(0, mid_y - h // 6)
    bottom_third = min(h, mid_y + h // 6)
    middle_crop = img[top_third:bottom_third, :]
    crops.append(("middle_strip", middle_crop))
    
    # Bottom half (for bottom case labels)
    bottom_half = img[h//2:, :]
    crops.append(("bottom_half", bottom_half))
    
    # Middle square
    mid_x = w // 2
    square_size = min(h, w) // 3
    middle_square = img[
        max(0, mid_y - square_size//2):min(h, mid_y + square_size//2),
        max(0, mid_x - square_size//2):min(w, mid_x + square_size//2)
    ]
    crops.append(("middle_square", middle_square))
    
    # Save crops for debugging
    if debug_path:
        for name, crop in crops:
            crop_path = os.path.join(debug_path, f"crop_{name}.png")
            cv2.imwrite(crop_path, crop)
    
    return crops

def enhance_for_character_recognition(img: np.ndarray) -> List[np.ndarray]:
    """Apply enhancements specifically for character recognition."""
    enhanced_images = []
    
    # Convert to grayscale if not already
    if len(img.shape) > 2 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    
    # 1. Basic enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced_images.append(("clahe", enhanced))
    
    # 2. High contrast for character edges
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    enhanced_images.append(("binary", binary))
    
    # 3. Edge enhancement for character boundaries
    edges = cv2.Canny(enhanced, 100, 200)
    enhanced_images.append(("edges", edges))
    
    # 4. Morphological operations to connect character parts
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    enhanced_images.append(("morph", eroded))
    
    # 5. Super-resolution (4x upscaling)
    upscaled = cv2.resize(enhanced, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
    enhanced_images.append(("upscaled", upscaled))
    
    # 6. Sharpening for better character definition
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
    enhanced_images.append(("sharpened", sharpened))
    
    # Save enhanced images
    for name, img in enhanced_images:
        cv2.imwrite(os.path.join(DEBUG_DIR, f"enhanced_{name}.png"), img)
    
    return [img for _, img in enhanced_images]

def test_api_with_image(image_path: str, params: Dict) -> Tuple[bool, float, Optional[str]]:
    """Test the OCR API with a specific image and parameters."""
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
            
            # Get all detected serials
            serials = [(s["serial"], s["confidence"]) for s in result["serials"]]
            
            # Apply character corrections to all detected serials
            all_variants = []
            for serial, conf in serials:
                corrected_variants = apply_character_corrections(serial)
                for variant in corrected_variants:
                    all_variants.append((variant, conf))
            
            # Check if any variant matches the known serial
            for variant, conf in all_variants:
                if variant == KNOWN_SERIAL:
                    return True, conf, variant
            
            # If no exact match, return the top result
            return True, serials[0][1], serials[0][0]
            
    except Exception as e:
        print(f"Exception: {e}")
        return False, 0.0, None

def save_temp_image(img: np.ndarray, name: str) -> str:
    """Save a temporary image and return its path."""
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    cv2.imwrite(path, img)
    return path

def main():
    print(f"Optimizing character recognition for: {IMAGE_PATH}")
    print(f"Target serial number: {KNOWN_SERIAL}")
    
    # Crop to potential serial regions
    print("\nCropping to potential serial regions...")
    crops = crop_to_serial_region(IMAGE_PATH, DEBUG_DIR)
    if not crops:
        print("Error: Could not process the image")
        return
    
    # Best parameters for character recognition in etched serials
    best_params = {
        "preset": "etched",
        "upscale_scale": 5.0,
        "mode": "gray",
        "roi": False,
        "glare_reduction": "division",
        "fine_rotation": True,
        "rotations": "0",
        "mag_ratio": 2.0,
        "low_text": 0.1,
        "text_threshold": 0.3,
    }
    
    # Test with original image first
    print("\nTesting with original image:")
    success, confidence, serial = test_api_with_image(IMAGE_PATH, best_params)
    if success:
        print(f"Detected: {serial} (confidence: {confidence:.2f})")
        if serial == KNOWN_SERIAL:
            print("✓ MATCH with target serial!")
        else:
            print(f"✗ NO MATCH with target serial ({KNOWN_SERIAL})")
            
            # Apply character corrections
            variants = apply_character_corrections(serial)
            print(f"Possible corrections: {variants}")
            if KNOWN_SERIAL in variants:
                print(f"✓ Found target serial after character correction!")
    
    # Test with each crop
    print("\nTesting with cropped regions:")
    for name, crop in crops:
        print(f"\nCrop: {name}")
        
        # Enhance the crop for character recognition
        enhanced_images = enhance_for_character_recognition(crop)
        
        for i, enhanced in enumerate(enhanced_images):
            # Save temporary image
            temp_path = save_temp_image(enhanced, f"temp_{name}_{i}")
            
            # Test with API
            success, confidence, serial = test_api_with_image(temp_path, best_params)
            
            if success:
                print(f"Enhancement {i}: Detected {serial} (confidence: {confidence:.2f})")
                
                # Apply character corrections
                variants = apply_character_corrections(serial)
                if KNOWN_SERIAL in variants:
                    print(f"✓ MATCH with target serial after correction!")
                    print(f"Original detection: {serial}")
                    print(f"Corrected to: {KNOWN_SERIAL}")
                    
                    # Save the successful parameters and preprocessing
                    with open(os.path.join(DEBUG_DIR, "successful_params.txt"), "w") as f:
                        f.write(f"Original image: {IMAGE_PATH}\n")
                        f.write(f"Crop: {name}\n")
                        f.write(f"Enhancement: {i}\n")
                        f.write(f"Original detection: {serial}\n")
                        f.write(f"Corrected to: {KNOWN_SERIAL}\n")
                        f.write(f"Confidence: {confidence:.2f}\n\n")
                        f.write("Parameters:\n")
                        for k, v in best_params.items():
                            f.write(f"  {k}: {v}\n")
                    
                    print("\nSuccess! Parameters saved to successful_params.txt")
                    return
    
    print("\nOptimization complete. Check the debug directory for processed images.")

if __name__ == "__main__":
    main()
