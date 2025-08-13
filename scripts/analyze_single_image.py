import os
import cv2
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional, Set
import time

# Configuration
IMAGE_PATH = "Apple serial/IMG-20250813-WA0039.jpg"
KNOWN_SERIAL = "C02Y95A8JG5H"
DEBUG_DIR = "exports/debug/single_image_analysis"
API_URL = "http://localhost:8000/process-serial"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)

def save_debug_image(img: np.ndarray, name: str) -> str:
    """Save an image for debugging and return its path."""
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    cv2.imwrite(path, img)
    return path

def apply_zoom_and_preprocess(image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """Apply various zoom and preprocessing techniques to the image."""
    results = []
    h, w = image.shape[:2]
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Save original grayscale
    save_debug_image(gray, "01_gray")
    results.append(("gray", gray))
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    save_debug_image(enhanced, "02_clahe")
    results.append(("clahe", enhanced))
    
    # Create bottom half zoom (where serial numbers often appear on MacBooks)
    bottom_half = image[h//2:, :]
    save_debug_image(bottom_half, "03_bottom_half")
    results.append(("bottom_half", bottom_half))
    
    # Create middle zoom (focused on the center where serial often is)
    mid_y = h // 2
    mid_x = w // 2
    zoom_size_h = h // 3
    zoom_size_w = w // 2
    
    middle_zoom = image[
        max(0, mid_y - zoom_size_h//2):min(h, mid_y + zoom_size_h//2),
        max(0, mid_x - zoom_size_w//2):min(w, mid_x + zoom_size_w//2)
    ]
    save_debug_image(middle_zoom, "04_middle_zoom")
    results.append(("middle_zoom", middle_zoom))
    
    # Apply preprocessing to the middle zoom
    if len(middle_zoom.shape) == 3:
        middle_gray = cv2.cvtColor(middle_zoom, cv2.COLOR_BGR2GRAY)
    else:
        middle_gray = middle_zoom.copy()
    
    # Apply CLAHE to middle zoom
    middle_enhanced = clahe.apply(middle_gray)
    save_debug_image(middle_enhanced, "05_middle_enhanced")
    results.append(("middle_enhanced", middle_enhanced))
    
    # Apply bilateral filter to middle zoom
    bilateral = cv2.bilateralFilter(middle_enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    save_debug_image(bilateral, "06_bilateral")
    results.append(("bilateral", bilateral))
    
    # Apply sharpening to middle zoom
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilateral, -1, kernel)
    save_debug_image(sharpened, "07_sharpened")
    results.append(("sharpened", sharpened))
    
    # Apply glare reduction (division method)
    background = cv2.GaussianBlur(middle_gray, (51, 51), 0)
    divided = cv2.divide(middle_gray, background, scale=255)
    save_debug_image(divided, "08_divided")
    results.append(("divided", divided))
    
    # Upscale middle zoom
    upscaled = cv2.resize(middle_enhanced, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
    save_debug_image(upscaled, "09_upscaled")
    results.append(("upscaled", upscaled))
    
    # Create horizontal strips
    num_strips = 3
    strip_height = h // num_strips
    for i in range(num_strips):
        y_start = i * strip_height
        y_end = min(y_start + strip_height, h)
        strip = image[y_start:y_end, :]
        save_debug_image(strip, f"10_strip_{i+1}")
        results.append((f"strip_{i+1}", strip))
    
    return results

def test_image_locally():
    """Process the image locally without using the API."""
    print(f"Analyzing image: {IMAGE_PATH}")
    print(f"Target serial: {KNOWN_SERIAL}")
    
    # Read the image
    image = cv2.imread(IMAGE_PATH)
    if image is None:
        print(f"Error reading image: {IMAGE_PATH}")
        return
    
    # Save original for reference
    save_debug_image(image, "00_original")
    
    # Apply zoom and preprocessing
    processed_images = apply_zoom_and_preprocess(image)
    print(f"Created {len(processed_images)} processed versions")
    
    # Print instructions for manual verification
    print("\nProcessed images saved to:", DEBUG_DIR)
    print("To manually check the images:")
    print("1. Open the debug directory")
    print("2. Look for the serial number in each image")
    print("3. The best preprocessing should make the serial number most visible")
    
    # Suggest best parameters for API
    print("\nRecommended API parameters for this image:")
    print("""
    {
        "preset": "etched",
        "upscale_scale": 5.0,
        "mode": "gray",
        "roi": False,
        "glare_reduction": "division",
        "fine_rotation": True,
        "rotations": "0",
        "mag_ratio": 2.0,
        "low_text": 0.1,
        "text_threshold": 0.3
    }
    """)

def main():
    test_image_locally()

if __name__ == "__main__":
    main()
