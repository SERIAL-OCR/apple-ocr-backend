import os
import sys
import cv2
import numpy as np
import requests
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import time

# Configuration
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/apple_serial_zoom_results.csv"
DEBUG_DIR = "exports/debug/apple_serials_zoom"
API_URL = "http://localhost:8000/process-serial"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Character confusion mapping for Apple serial numbers
CHAR_CONFUSION = {
    '0': {'O', 'D', 'Q'},
    '1': {'I', 'L', 'l'},
    '2': {'Z'},
    '5': {'S'},
    '6': {'G', 'C'},
    '8': {'B'},
    'A': {'4', 'R'},
    'G': {'6', 'C'},
    'O': {'0', 'Q', 'D'},
    'S': {'5'},
    'Z': {'2'},
    'B': {'8', '3'},
    'I': {'1', 'l', 'J'},
    'L': {'1', 'I'},
}

def load_labels(labels_path: str) -> Dict[str, str]:
    """Load ground truth labels from CSV."""
    labels = {}
    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'filename' in row and 'serial' in row and row['serial']:
                    labels[row['filename']] = row['serial'].strip().upper()
    return labels

def generate_character_variants(text: str) -> Set[str]:
    """Generate all possible variants based on character confusion."""
    if not text:
        return set()
    
    # Start with the original text
    variants = {text}
    
    # For each position, try all possible character substitutions
    for i, char in enumerate(text):
        char_upper = char.upper()
        # Check if this character has common confusions
        if char_upper in CHAR_CONFUSION:
            # For each possible confusion of this character
            for confused_char in CHAR_CONFUSION[char_upper]:
                # Create new variants by substituting at this position
                new_variants = set()
                for variant in variants:
                    new_variant = variant[:i] + confused_char + variant[i+1:]
                    new_variants.add(new_variant)
                variants.update(new_variants)
    
    return variants

def detect_text_regions(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect potential text regions in the image.
    Returns a list of (x, y, w, h) rectangles.
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by size
    h, w = gray.shape
    min_area = (w * h) * 0.001  # Minimum area (0.1% of image)
    max_area = (w * h) * 0.1    # Maximum area (10% of image)
    
    text_regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(contour)
            # Filter by aspect ratio (typical for text)
            aspect_ratio = w / h if h > 0 else 0
            if 1.5 < aspect_ratio < 15:  # Text is usually wider than tall
                # Ensure region is valid (not empty)
                if w > 0 and h > 0 and x >= 0 and y >= 0 and x + w <= image.shape[1] and y + h <= image.shape[0]:
                    text_regions.append((x, y, w, h))
    
    return text_regions

def create_zoom_regions(image: np.ndarray, debug_prefix: str = "") -> List[Tuple[str, np.ndarray]]:
    """
    Create multiple zoomed versions of the image focusing on potential text regions.
    Returns a list of (name, zoomed_image) tuples.
    """
    h, w = image.shape[:2]
    results = []
    
    # Add the original image
    results.append(("original", image))
    
    # Create fixed zoom regions (horizontal strips)
    num_strips = 3
    strip_height = h // num_strips
    for i in range(num_strips):
        y_start = i * strip_height
        y_end = min(y_start + strip_height, h)
        strip = image[y_start:y_end, :]
        results.append((f"strip_{i+1}", strip))
        
        # Save debug image
        if debug_prefix:
            debug_path = os.path.join(DEBUG_DIR, f"{debug_prefix}_strip_{i+1}.png")
            cv2.imwrite(debug_path, strip)
    
    # Detect text regions
    text_regions = detect_text_regions(image)
    
    # For each text region, create a zoomed version with padding
    padding = 20  # pixels
    for i, (x, y, region_w, region_h) in enumerate(text_regions):
        # Add padding
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(w, x + region_w + padding)
        y2 = min(h, y + region_h + padding)
        
        # Ensure region is valid
        if x1 < x2 and y1 < y2:
            # Extract the region
            region = image[y1:y2, x1:x2]
            
            # Verify region is not empty
            if region.size > 0:
                results.append((f"region_{i+1}", region))
                
                # Save debug image
                if debug_prefix:
                    debug_path = os.path.join(DEBUG_DIR, f"{debug_prefix}_region_{i+1}.png")
                    cv2.imwrite(debug_path, region)
    
    # Create zoomed middle section (where serial numbers often appear)
    mid_y = h // 2
    mid_x = w // 2
    zoom_size_h = h // 3
    zoom_size_w = w // 2
    
    y1 = max(0, mid_y - zoom_size_h//2)
    y2 = min(h, mid_y + zoom_size_h//2)
    x1 = max(0, mid_x - zoom_size_w//2)
    x2 = min(w, mid_x + zoom_size_w//2)
    
    if y1 < y2 and x1 < x2:
        middle_zoom = image[y1:y2, x1:x2]
        if middle_zoom.size > 0:
            results.append(("middle_zoom", middle_zoom))
            
            # Save debug image
            if debug_prefix:
                debug_path = os.path.join(DEBUG_DIR, f"{debug_prefix}_middle_zoom.png")
                cv2.imwrite(debug_path, middle_zoom)
    
    # Create bottom half zoom (where serial numbers often appear on MacBooks)
    if h > 1:  # Ensure image has height
        bottom_half = image[h//2:, :]
        if bottom_half.size > 0:
            results.append(("bottom_half", bottom_half))
            
            # Save debug image
            if debug_prefix:
                debug_path = os.path.join(DEBUG_DIR, f"{debug_prefix}_bottom_half.png")
                cv2.imwrite(debug_path, bottom_half)
    
    return results

def preprocess_for_apple_serial(image: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """Apply specialized preprocessing for Apple serial numbers."""
    preprocessed = []
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Apply bilateral filter to smooth while preserving edges
    bilateral = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Sharpen the image
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilateral, -1, kernel)
    
    # Division (good for metallic surfaces)
    background = cv2.GaussianBlur(gray, (51, 51), 0)
    divided = cv2.divide(gray, background, scale=255)
    
    # Upscale for better OCR
    upscaled = cv2.resize(enhanced, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
    
    # Return preprocessed versions
    return [
        ("enhanced", enhanced),
        ("bilateral", bilateral),
        ("sharpened", sharpened),
        ("divided", divided)
    ]

def save_temp_image(img: np.ndarray, name: str) -> str:
    """Save a temporary image and return its path."""
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    cv2.imwrite(path, img)
    return path

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
            
            # Return the top result
            return True, serials[0][1], serials[0][0]
            
    except Exception as e:
        print(f"Exception: {e}")
        return False, 0.0, None

def process_image(image_path: str, ground_truth: Optional[str] = None) -> Dict:
    """Process a single image with zoom regions and return results."""
    filename = os.path.basename(image_path)
    print(f"\nProcessing {filename}...")
    
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error reading image: {image_path}")
        return {
            "filename": filename,
            "success": False,
            "confidence": 0.0,
            "detected_serial": None,
            "ground_truth": ground_truth,
            "match": False,
            "match_with_correction": False,
            "zoom_region": None
        }
    
    # Save original for reference
    debug_path = os.path.join(DEBUG_DIR, f"original_{filename}")
    cv2.imwrite(debug_path, image)
    
    # Create zoom regions
    zoom_regions = create_zoom_regions(image, debug_prefix=filename.split('.')[0])
    
    # Parameters optimized for Apple serial number recognition
    params = {
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
    
    best_result = None
    best_confidence = 0.0
    best_region_name = None
    
    # Try each zoom region
    for region_name, region_img in zoom_regions:
        print(f"  Testing {region_name} region...")
        
        # Save the region for API testing
        temp_path = save_temp_image(region_img, f"{filename}_{region_name}")
        
        # Try different preprocessing on this region
        for preproc_name, preproc_img in preprocess_for_apple_serial(region_img):
            # Save preprocessed image
            preproc_path = save_temp_image(preproc_img, f"{filename}_{region_name}_{preproc_name}")
            
            # Test with API
            success, confidence, serial = test_api_with_image(preproc_path, params)
            
            if success:
                print(f"    {region_name}_{preproc_name}: Detected {serial} (confidence: {confidence:.2f})")
                
                # Check if this is the best result so far
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = (success, confidence, serial)
                    best_region_name = f"{region_name}_{preproc_name}"
                
                # Check if it matches ground truth
                if ground_truth and serial.upper() == ground_truth.upper():
                    print(f"    ✓ EXACT MATCH with ground truth!")
                    return {
                        "filename": filename,
                        "success": True,
                        "confidence": confidence,
                        "detected_serial": serial,
                        "ground_truth": ground_truth,
                        "match": True,
                        "match_with_correction": False,
                        "zoom_region": f"{region_name}_{preproc_name}"
                    }
                
                # Check if it matches with character correction
                if ground_truth:
                    variants = generate_character_variants(serial)
                    for variant in variants:
                        if variant.upper() == ground_truth.upper():
                            print(f"    ✓ MATCH after character correction: {serial} -> {ground_truth}")
                            return {
                                "filename": filename,
                                "success": True,
                                "confidence": confidence,
                                "detected_serial": serial,
                                "ground_truth": ground_truth,
                                "match": False,
                                "match_with_correction": True,
                                "zoom_region": f"{region_name}_{preproc_name}"
                            }
    
    # Return the best result if any
    if best_result:
        success, confidence, serial = best_result
        return {
            "filename": filename,
            "success": True,
            "confidence": confidence,
            "detected_serial": serial,
            "ground_truth": ground_truth,
            "match": False,
            "match_with_correction": False,
            "zoom_region": best_region_name
        }
    
    # No results found
    return {
        "filename": filename,
        "success": False,
        "confidence": 0.0,
        "detected_serial": None,
        "ground_truth": ground_truth,
        "match": False,
        "match_with_correction": False,
        "zoom_region": None
    }

def main():
    # Load ground truth labels
    labels_path = os.path.join(IMAGE_DIR, "labels.csv")
    labels = load_labels(labels_path)
    
    # Get all image files
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Process each image
    results = []
    
    for img_file in image_files:
        img_path = os.path.join(IMAGE_DIR, img_file)
        ground_truth = labels.get(img_file)
        
        # Only process images with ground truth for now
        if ground_truth:
            print(f"Processing {img_file} (Ground truth: {ground_truth})")
            result = process_image(img_path, ground_truth)
            results.append(result)
    
    # Calculate statistics
    total = len(results)
    detected = sum(1 for r in results if r["success"])
    matches = sum(1 for r in results if r["match"])
    matches_with_correction = sum(1 for r in results if r["match_with_correction"])
    
    detection_rate = (detected / total) * 100 if total > 0 else 0
    accuracy = (matches / detected) * 100 if detected > 0 else 0
    accuracy_with_correction = ((matches + matches_with_correction) / detected) * 100 if detected > 0 else 0
    
    print("\n=== RESULTS ===")
    print(f"Total images with ground truth: {total}")
    print(f"Serials detected: {detected} ({detection_rate:.1f}%)")
    print(f"Exact matches: {matches} ({accuracy:.1f}% of detected)")
    print(f"Matches with character correction: {matches_with_correction}")
    print(f"Total accuracy with correction: {accuracy_with_correction:.1f}%")
    
    # Write results to CSV
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = [
            'filename', 'success', 'confidence', 'detected_serial', 
            'ground_truth', 'match', 'match_with_correction', 'zoom_region'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"Debug images saved to {DEBUG_DIR}")

if __name__ == "__main__":
    main()
