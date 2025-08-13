import os
import cv2
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional, Set
import re

# Configuration
IMAGE_DIR = "Apple serial"
DEBUG_DIR = "exports/debug/enhanced_recognition"
API_URL = "http://localhost:8000/process-serial"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)

# Apple serial number pattern (12 alphanumeric characters)
APPLE_SERIAL_PATTERN = re.compile(r'^[A-Z0-9]{12}$')

# Common Apple serial number prefixes
COMMON_PREFIXES = {
    'C02', 'F', 'G', 'W', 'DM', 'C1M', 'C17', 'C07', 'YM', 'VM'
}

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

def save_debug_image(img: np.ndarray, name: str) -> str:
    """Save an image for debugging and return its path."""
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    cv2.imwrite(path, img)
    return path

def enhance_for_character_recognition(image: np.ndarray, name_prefix: str = "") -> List[np.ndarray]:
    """Apply specialized enhancements for character recognition."""
    enhanced_images = []
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # 1. Basic enhancement with CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    save_debug_image(enhanced, f"{name_prefix}_01_clahe")
    enhanced_images.append(enhanced)
    
    # 2. Apply bilateral filter to preserve edges while reducing noise
    bilateral = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    save_debug_image(bilateral, f"{name_prefix}_02_bilateral")
    enhanced_images.append(bilateral)
    
    # 3. Sharpen to enhance character edges
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(bilateral, -1, kernel_sharpen)
    save_debug_image(sharpened, f"{name_prefix}_03_sharpened")
    enhanced_images.append(sharpened)
    
    # 4. Adaptive thresholding for binarization
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 45, 9
    )
    save_debug_image(thresh, f"{name_prefix}_04_threshold")
    enhanced_images.append(thresh)
    
    # 5. Morphological operations to clean up binary image
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    save_debug_image(morph, f"{name_prefix}_05_morphology")
    enhanced_images.append(morph)
    
    # 6. Edge enhancement using Canny
    edges = cv2.Canny(bilateral, 100, 200)
    save_debug_image(edges, f"{name_prefix}_06_edges")
    enhanced_images.append(edges)
    
    # 7. Background division (good for metallic surfaces)
    background = cv2.GaussianBlur(gray, (51, 51), 0)
    divided = cv2.divide(gray, background, scale=255)
    save_debug_image(divided, f"{name_prefix}_07_divided")
    enhanced_images.append(divided)
    
    # 8. High-pass filter to enhance text edges
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    highpass = cv2.subtract(gray, blurred)
    highpass = cv2.normalize(highpass, None, 0, 255, cv2.NORM_MINMAX)
    save_debug_image(highpass, f"{name_prefix}_08_highpass")
    enhanced_images.append(highpass)
    
    # 9. Super-resolution (4x upscaling)
    upscaled = cv2.resize(enhanced, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_CUBIC)
    save_debug_image(upscaled, f"{name_prefix}_09_upscaled")
    enhanced_images.append(upscaled)
    
    return enhanced_images

def apply_character_corrections(detected: str) -> List[str]:
    """Apply character corrections based on common OCR confusions."""
    if not detected or len(detected) != 12:
        return [detected] if detected else []
    
    variants = [detected]
    
    # Check for common Apple serial prefixes
    prefix = detected[:3]
    if prefix not in COMMON_PREFIXES:
        # Try correcting the prefix
        for common_prefix in COMMON_PREFIXES:
            if len(common_prefix) <= 3:
                corrected = common_prefix + detected[len(common_prefix):]
                variants.append(corrected)
    
    # Generate variants by replacing commonly confused characters
    for i, char in enumerate(detected):
        if char in CHAR_CONFUSION:
            for confused_char in CHAR_CONFUSION[char]:
                for variant in list(variants):  # Create a copy to avoid modifying during iteration
                    corrected = variant[:i] + confused_char + variant[i+1:]
                    variants.append(corrected)
    
    # Filter to keep only valid 12-character alphanumeric serials
    valid_variants = [v for v in variants if APPLE_SERIAL_PATTERN.match(v)]
    
    return valid_variants

def extract_text_with_tesseract(image, config='--oem 1 --psm 7'):
    """Extract text using Tesseract OCR with optimized settings for serial numbers."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(
            image, 
            config=config,
            lang='eng'
        )
        return text.strip()
    except Exception as e:
        print(f"Tesseract error: {e}")
        return ""

def process_image_for_serial(image_path: str, known_serial: Optional[str] = None):
    """Process a single image with optimized settings for Apple serial number recognition."""
    print(f"\nProcessing {image_path}")
    if known_serial:
        print(f"Known serial: {known_serial}")
    
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error reading image: {image_path}")
        return
    
    # Save original for reference
    filename = os.path.basename(image_path)
    save_debug_image(image, f"{filename}_00_original")
    
    # Create zoom regions
    h, w = image.shape[:2]
    
    # Bottom half (where serial numbers often appear on MacBooks)
    bottom_half = image[h//2:, :]
    save_debug_image(bottom_half, f"{filename}_bottom_half")
    
    # Middle section (focused on center)
    mid_y = h // 2
    mid_x = w // 2
    zoom_size_h = h // 3
    zoom_size_w = w // 2
    
    middle = image[
        max(0, mid_y - zoom_size_h//2):min(h, mid_y + zoom_size_h//2),
        max(0, mid_x - zoom_size_w//2):min(w, mid_x + zoom_size_w//2)
    ]
    save_debug_image(middle, f"{filename}_middle")
    
    # Process each region
    regions = [
        ("original", image),
        ("bottom_half", bottom_half),
        ("middle", middle)
    ]
    
    results = []
    
    for region_name, region in regions:
        print(f"\nProcessing {region_name} region:")
        
        # Apply character recognition enhancements
        enhanced_images = enhance_for_character_recognition(region, f"{filename}_{region_name}")
        
        # Try Tesseract OCR with different configurations
        psm_modes = [7, 8, 6, 11]  # Different page segmentation modes
        
        for i, enhanced in enumerate(enhanced_images):
            enhancement_name = [
                "clahe", "bilateral", "sharpened", "threshold", 
                "morphology", "edges", "divided", "highpass", "upscaled"
            ][i]
            
            print(f"  Testing {enhancement_name}...")
            
            # Try different Tesseract configurations
            for psm in psm_modes:
                config = f'--oem 1 --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                text = extract_text_with_tesseract(enhanced, config)
                
                # Clean up the text
                text = ''.join(c for c in text if c.isalnum())
                
                if text and len(text) >= 10:  # At least 10 characters to be a potential serial
                    print(f"    Detected: {text} (PSM {psm})")
                    
                    # Apply character corrections
                    variants = apply_character_corrections(text)
                    
                    # Check if any variant matches the known serial
                    if known_serial:
                        for variant in variants:
                            if variant.upper() == known_serial.upper():
                                print(f"    ✓ MATCH after correction: {text} -> {known_serial}")
                                results.append({
                                    "region": region_name,
                                    "enhancement": enhancement_name,
                                    "psm": psm,
                                    "detected": text,
                                    "corrected": variant,
                                    "match": True
                                })
                                break
                        else:
                            results.append({
                                "region": region_name,
                                "enhancement": enhancement_name,
                                "psm": psm,
                                "detected": text,
                                "variants": variants,
                                "match": False
                            })
                    else:
                        results.append({
                            "region": region_name,
                            "enhancement": enhancement_name,
                            "psm": psm,
                            "detected": text,
                            "variants": variants,
                            "match": False
                        })
    
    # Summarize results
    print("\n=== RESULTS ===")
    print(f"Total detections: {len(results)}")
    
    if known_serial:
        matches = [r for r in results if r.get("match", False)]
        print(f"Matches with known serial: {len(matches)}")
        
        if matches:
            print("\nBest matching configurations:")
            for match in matches:
                print(f"  Region: {match['region']}")
                print(f"  Enhancement: {match['enhancement']}")
                print(f"  PSM mode: {match['psm']}")
                print(f"  Detected: {match['detected']}")
                print(f"  Corrected to: {match['corrected']}")
                print()
    
    # Recommend optimal settings
    print("\nRecommended settings for Apple serial number recognition:")
    print("""
1. Image preprocessing:
   - Apply CLAHE with clipLimit=3.0
   - Use bilateral filter (d=9, sigmaColor=75, sigmaSpace=75)
   - Apply sharpening with kernel [[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]
   - Use background division for metallic surfaces
   - Upscale by 4x for small text

2. OCR parameters:
   - Set allowlist to "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
   - Use low_text=0.1 and text_threshold=0.3
   - Set mag_ratio=2.0 for better magnification
   - Try multiple PSM modes (7, 8, 6, 11)

3. Post-processing:
   - Apply character correction for common confusions (0/O, 1/I/L, etc.)
   - Validate against known Apple serial number patterns
   - Check for common Apple prefixes (C02, F, G, etc.)
   - Use context (position on device) to improve confidence
    """)
    
    print("\nProcessed images saved to:", DEBUG_DIR)

def main():
    # Process specific image with known serial
    image_path = "Apple serial/IMG-20250813-WA0039.jpg"
    known_serial = "C02Y95A8JG5H"
    
    process_image_for_serial(image_path, known_serial)

if __name__ == "__main__":
    main()
