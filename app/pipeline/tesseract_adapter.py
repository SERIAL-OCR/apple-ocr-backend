"""
Tesseract OCR adapter for Apple serial number recognition.
Used as a fallback when EasyOCR fails to produce high-confidence results.
"""

from __future__ import annotations

import os
import tempfile
import logging
from typing import List, Tuple, Optional, Dict

import cv2
import numpy as np
import pytesseract

from app.utils.validation import is_valid_apple_serial

logger = logging.getLogger(__name__)

# Define allowed characters for Apple serial numbers
_ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Character substitution map for common OCR errors
_CORRECTION_MAP = {
    '0': ['O', 'D', 'Q'],
    '1': ['I', 'L', '|'],
    '2': ['Z'],
    '5': ['S'],
    '6': ['G'],
    '7': ['T'],
    '8': ['B'],
}


def _get_tesseract_path() -> Optional[str]:
    """Get Tesseract executable path from environment or use default."""
    tesseract_cmd = os.environ.get("TESSERACT_CMD")
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        return tesseract_cmd
    
    # Try common paths
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows
        r"/usr/bin/tesseract",  # Linux
        r"/usr/local/bin/tesseract",  # macOS
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def _configure_tesseract() -> bool:
    """Configure Tesseract path and check if it's available."""
    tesseract_path = _get_tesseract_path()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.info(f"Tesseract configured with path: {tesseract_path}")
        return True
    else:
        logger.warning("Tesseract not found. Fallback mechanism will be disabled.")
        return False


# Initialize Tesseract on module load
TESSERACT_AVAILABLE = _configure_tesseract()


def _preprocess_for_tesseract(image: np.ndarray) -> List[np.ndarray]:
    """
    Preprocess image for Tesseract OCR with multiple processing paths.
    
    Args:
        image: Input image (grayscale or BGR)
        
    Returns:
        List of preprocessed images to try with Tesseract
    """
    # Ensure grayscale
    if len(image.shape) > 2:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Create multiple preprocessing paths
    preprocessed = []
    
    # 1. Original grayscale with adaptive threshold
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 31, 10)
    preprocessed.append(thresh)
    
    # 2. Inverted image (for light text on dark background)
    inverted = cv2.bitwise_not(gray)
    thresh_inv = cv2.adaptiveThreshold(inverted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 31, 10)
    preprocessed.append(thresh_inv)
    
    # 3. Sharpened image
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    thresh_sharp = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 31, 10)
    preprocessed.append(thresh_sharp)
    
    # 4. Dilated image (helps with thin text)
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    preprocessed.append(dilated)
    
    # 5. Eroded image (helps with thick text)
    eroded = cv2.erode(thresh, kernel, iterations=1)
    preprocessed.append(eroded)
    
    # Scale up images for better OCR (Tesseract works better with larger text)
    scaled_images = []
    for img in preprocessed:
        # Scale to 2x and 3x
        scaled_2x = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        scaled_3x = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        scaled_images.extend([img, scaled_2x, scaled_3x])
    
    return scaled_images


def _filter_tesseract_result(text: str) -> str:
    """Filter and clean Tesseract OCR result."""
    # Remove whitespace and convert to uppercase
    text = text.strip().upper().replace(" ", "")
    
    # Filter out non-alphanumeric characters
    text = ''.join(c for c in text if c in _ALLOWED_CHARS)
    
    return text


def _generate_candidate_serials(text: str) -> List[str]:
    """Generate possible serial number candidates from OCR text."""
    candidates = [text]
    
    # Try to extract 12-character sequences that could be serials
    if len(text) > 12:
        for i in range(len(text) - 11):
            candidates.append(text[i:i+12])
    
    # Apply character corrections
    corrected_candidates = []
    for candidate in candidates:
        if len(candidate) == 12:
            corrected_candidates.append(candidate)
            
            # Generate variations by replacing commonly confused characters
            for i, char in enumerate(candidate):
                for digit, confused_chars in _CORRECTION_MAP.items():
                    if char in confused_chars:
                        corrected = candidate[:i] + digit + candidate[i+1:]
                        corrected_candidates.append(corrected)
    
    # Filter out duplicates
    return list(set(corrected_candidates))


def extract_serials_with_tesseract(
    image: np.ndarray,
    min_confidence: float = 0.0,
    psm_modes: List[int] = [6, 7, 8, 13],  # Page segmentation modes to try
) -> List[Tuple[str, float]]:
    """
    Extract serial numbers using Tesseract OCR.
    
    Args:
        image: Input image
        min_confidence: Minimum confidence threshold
        psm_modes: Tesseract page segmentation modes to try
        
    Returns:
        List of (serial, confidence) tuples
    """
    if not TESSERACT_AVAILABLE:
        logger.warning("Tesseract not available for fallback OCR")
        return []
    
    # Preprocess image with multiple techniques
    preprocessed_images = _preprocess_for_tesseract(image)
    
    all_candidates = []
    
    # Try different preprocessing and PSM modes
    for img in preprocessed_images:
        for psm in psm_modes:
            try:
                # Configure Tesseract
                config = f"--psm {psm} --oem 1 -c tessedit_char_whitelist={_ALLOWED_CHARS}"
                
                # Get OCR results with confidence data
                data = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
                
                # Extract text and confidence
                for i, text in enumerate(data['text']):
                    if text.strip():
                        conf = float(data['conf'][i]) / 100.0  # Normalize to 0-1 range
                        
                        if conf >= min_confidence:
                            filtered_text = _filter_tesseract_result(text)
                            candidates = _generate_candidate_serials(filtered_text)
                            
                            for candidate in candidates:
                                if is_valid_apple_serial(candidate):
                                    all_candidates.append((candidate, conf))
            except Exception as e:
                logger.error(f"Tesseract error with PSM {psm}: {str(e)}")
    
    # Sort by confidence and remove duplicates
    unique_results = {}
    for serial, conf in all_candidates:
        if serial not in unique_results or conf > unique_results[serial]:
            unique_results[serial] = conf
    
    # Return sorted by confidence
    return sorted([(s, c) for s, c in unique_results.items()], key=lambda x: x[1], reverse=True)
