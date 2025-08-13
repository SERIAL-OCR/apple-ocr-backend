import os
import sys
import cv2
import numpy as np
import requests
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

# Configuration
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/apple_serial_results.csv"
DEBUG_DIR = "exports/debug/apple_serials"
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

# Apple serial number pattern (12 alphanumeric characters)
APPLE_SERIAL_PATTERN = r'^[A-Z0-9]{12}$'

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

def preprocess_for_apple_serial(image: np.ndarray) -> List[np.ndarray]:
    """Apply specialized preprocessing for Apple serial numbers."""
    preprocessed = []
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Basic preprocessing
    preprocessed.append(("gray", gray))
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    preprocessed.append(("clahe", enhanced))
    
    # Apply bilateral filter to smooth while preserving edges
    bilateral = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    preprocessed.append(("bilateral", bilateral))
    
    # Sharpen the image
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilateral, -1, kernel)
    preprocessed.append(("sharpened", sharpened))
    
    # Division (good for metallic surfaces)
    background = cv2.GaussianBlur(gray, (51, 51), 0)
    divided = cv2.divide(gray, background, scale=255)
    preprocessed.append(("divided", divided))
    
    # Upscale for better OCR
    upscaled = cv2.resize(enhanced, None, fx=4.0, fy=4.0, interpolation=cv2.CUBIC)
    preprocessed.append(("upscaled", upscaled))
    
    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 45, 9
    )
    preprocessed.append(("thresh", thresh))
    
    return preprocessed

def process_image(image_path: str, ground_truth: Optional[str] = None) -> Dict:
    """Process a single image and return results."""
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
            "correction_applied": False
        }
    
    # Save original for reference
    debug_path = os.path.join(DEBUG_DIR, f"original_{filename}")
    cv2.imwrite(debug_path, image)
    
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
    
    try:
        # Send the image to the API
        with open(image_path, "rb") as f:
            files = {"image": (filename, f, "image/jpeg")}
            
            response = requests.post(
                API_URL,
                files=files,
                params=params,
                timeout=90
            )
            
            if response.status_code != 200:
                print(f"Error processing {filename}: {response.status_code} - {response.text}")
                return {
                    "filename": filename,
                    "success": False,
                    "confidence": 0.0,
                    "detected_serial": None,
                    "ground_truth": ground_truth,
                    "match": False,
                    "match_with_correction": False,
                    "correction_applied": False
                }
            
            result = response.json()
            
            # Check if any serials were detected
            if not result.get("serials"):
                print(f"No serials found in {filename}")
                return {
                    "filename": filename,
                    "success": False,
                    "confidence": 0.0,
                    "detected_serial": None,
                    "ground_truth": ground_truth,
                    "match": False,
                    "match_with_correction": False,
                    "correction_applied": False
                }
            
            # Get the top result
            top_serial = result["serials"][0]
            detected = top_serial["serial"]
            confidence = top_serial["confidence"]
            
            print(f"Detected: {detected} (confidence: {confidence:.2f})")
            
            # Check if it matches ground truth
            match = False
            match_with_correction = False
            correction_applied = False
            
            if ground_truth:
                match = (detected.upper() == ground_truth.upper())
                
                # If no direct match, try character corrections
                if not match:
                    variants = generate_character_variants(detected)
                    for variant in variants:
                        if variant.upper() == ground_truth.upper():
                            match_with_correction = True
                            correction_applied = True
                            print(f"Match after correction: {detected} -> {ground_truth}")
                            break
            
            return {
                "filename": filename,
                "success": True,
                "confidence": confidence,
                "detected_serial": detected,
                "ground_truth": ground_truth,
                "match": match,
                "match_with_correction": match_with_correction,
                "correction_applied": correction_applied
            }
            
    except Exception as e:
        print(f"Exception processing {filename}: {e}")
        return {
            "filename": filename,
            "success": False,
            "confidence": 0.0,
            "detected_serial": None,
            "ground_truth": ground_truth,
            "match": False,
            "match_with_correction": False,
            "correction_applied": False
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
    print(f"Total images: {total}")
    print(f"Serials detected: {detected} ({detection_rate:.1f}%)")
    print(f"Exact matches: {matches} ({accuracy:.1f}% of detected)")
    print(f"Matches with character correction: {matches_with_correction}")
    print(f"Total accuracy with correction: {accuracy_with_correction:.1f}%")
    
    # Write results to CSV
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = [
            'filename', 'success', 'confidence', 'detected_serial', 
            'ground_truth', 'match', 'match_with_correction', 'correction_applied'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\nResults written to {OUTPUT_CSV}")
    print(f"Debug images saved to {DEBUG_DIR}")

if __name__ == "__main__":
    main()
