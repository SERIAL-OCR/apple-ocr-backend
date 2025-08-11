from __future__ import annotations

from typing import Optional, Tuple, List

import cv2
import numpy as np
import easyocr

from app.utils.validation import is_valid_apple_serial


_reader: Optional[easyocr.Reader] = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        # Initialize English only for speed in MVP
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    file_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE for reflective surfaces
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Bilateral filter to preserve edges
    filtered = cv2.bilateralFilter(enhanced, d=7, sigmaColor=75, sigmaSpace=75)

    # Adaptive threshold to help OCR
    th = cv2.adaptiveThreshold(
        filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
    )

    return th


def extract_serials(image_bytes: bytes) -> List[Tuple[str, float]]:
    processed = preprocess_image(image_bytes)
    reader = _get_reader()

    # EasyOCR expects an image array (RGB). Convert binary to BGR already; convert to RGB.
    rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)

    results = reader.readtext(rgb, detail=1, paragraph=False)

    serials: List[Tuple[str, float]] = []
    for bbox, text, confidence in results:
        candidate = text.strip().upper().replace(" ", "")
        if is_valid_apple_serial(candidate):
            serials.append((candidate, float(confidence)))

    # Deduplicate by serial, keep highest confidence
    best: dict[str, float] = {}
    for s, c in serials:
        if s not in best or c > best[s]:
            best[s] = c

    return [(s, best[s]) for s in best]
