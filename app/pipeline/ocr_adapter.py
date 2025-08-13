from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Set, Dict, Any
import logging
import time
import os
from pathlib import Path

import cv2
import numpy as np
import easyocr

from app.utils.validation import is_valid_apple_serial
from app.config import OCR_SETTINGS
from app.utils.logging import Timer, log_ocr_timing, log_detection_miss, log_debug_asset


_reader: Optional[easyocr.Reader] = None
logger = logging.getLogger(__name__)


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        use_gpu = OCR_SETTINGS["use_gpu"]
        languages = OCR_SETTINGS["languages"]
        # Simple init log to help verify GPU path in logs
        try:
            import torch  # type: ignore
            gpu_info = f"cuda={torch.version.cuda}, available={torch.cuda.is_available()}"
        except Exception:
            gpu_info = "torch_unavailable"
        logger.info(f"[EasyOCR] Initializing Reader(langs={languages}, gpu={use_gpu}) [{gpu_info}]")
        _reader = easyocr.Reader(languages, gpu=use_gpu)
    return _reader


def _morphological_refine(binary_img: np.ndarray, k: int = 2) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    closed = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel, iterations=1)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)
    return opened


def _reduce_glare(image: np.ndarray, method: str = "tophat") -> np.ndarray:
    """Reduce glare and improve illumination uniformity.
    
    Args:
        image: Grayscale image
        method: "tophat" for morphological top-hat, "division" for background division,
                "adaptive" to choose automatically based on image statistics
    
    Returns:
        Image with reduced glare
    """
    # Auto-select method if "adaptive" is specified
    if method == "adaptive":
        # Calculate image statistics
        mean_val = np.mean(image)
        std_val = np.std(image)
        
        # If high mean and low std, likely has uniform glare - use division
        if mean_val > 180 and std_val < 50:
            method = "division"
        # If medium brightness with higher contrast, likely has spotty glare - use tophat
        else:
            method = "tophat"
        
        logger.debug(f"[Glare] Auto-selected: {method} (mean={mean_val:.1f}, std={std_val:.1f})")
    
    if method == "tophat":
        # Morphological top-hat to remove bright regions
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (50, 50))
        tophat = cv2.morphologyEx(image, cv2.MORPH_TOPHAT, kernel)
        # Enhance the result
        result = cv2.add(image, tophat)
        result = np.clip(result, 0, 255).astype(np.uint8)
    elif method == "division":
        # Background estimation and division
        # Estimate background using large Gaussian blur
        background = cv2.GaussianBlur(image, (51, 51), 0)
        # Divide original by background to normalize illumination
        result = cv2.divide(image, background, scale=255)
    else:
        result = image
    
    return result


def preprocess_image(
    image_bytes: bytes,
    clip_limit: float = 2.0,
    tile_grid: int = 8,
    bilateral_d: int = 7,
    bilateral_sigma_color: int = 75,
    bilateral_sigma_space: int = 75,
    thresh_block_size: int = 35,
    thresh_C: int = 11,
    morph_kernel: int = 2,
    upscale_scale: float = 2.0,
    mode: str = "binary",  # "binary" or "gray"
    glare_reduction: Optional[str] = None,  # None, "tophat", or "division"
    debug_save_path: Optional[str] = None,
) -> np.ndarray:
    file_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply glare reduction if requested
    if glare_reduction:
        gray = _reduce_glare(gray, method=glare_reduction)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    enhanced = clahe.apply(gray)

    filtered = cv2.bilateralFilter(
        enhanced, d=bilateral_d, sigmaColor=bilateral_sigma_color, sigmaSpace=bilateral_sigma_space
    )

    if mode == "gray":
        out = filtered
    else:
        th = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, thresh_block_size, thresh_C
        )
        out = _morphological_refine(th, k=morph_kernel)

    if upscale_scale and upscale_scale != 1.0:
        out = cv2.resize(out, None, fx=upscale_scale, fy=upscale_scale, interpolation=cv2.INTER_CUBIC)

    if debug_save_path:
        cv2.imwrite(debug_save_path, out)

    return out


_AMBIGUOUS_MAP: dict[str, str] = {
    "O": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "Q": "0",
    "G": "6",
}


def _expand_ambiguous(text: str) -> Set[str]:
    variants: Set[str] = {text}
    for idx, ch in enumerate(text):
        rep = _AMBIGUOUS_MAP.get(ch)
        if rep:
            for v in list(variants):
                variants.add(v[:idx] + rep + v[idx + 1 :])
    return variants


def _normalize_ambiguous(text: str) -> str:
    up = text.strip().upper()
    return "".join(_AMBIGUOUS_MAP.get(ch, ch) for ch in up)


def _rotate_image(img: np.ndarray, angle: float) -> np.ndarray:
    """
    Rotate image by specified angle.
    
    Args:
        img: Input image
        angle: Rotation angle in degrees (can be float for fine-grained rotations)
        
    Returns:
        Rotated image
    """
    # Handle common angles with optimized methods
    if abs(angle) < 0.001 or abs(angle % 360) < 0.001:
        return img
    if abs(angle % 180) < 0.001:
        return cv2.rotate(img, cv2.ROTATE_180)
    if abs(angle % 270) < 0.001:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if abs(angle % 90) < 0.001:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # For arbitrary angles (including fractional angles)
    h, w = img.shape[:2]
    
    # Calculate rotation matrix
    # The negative sign is because OpenCV rotates counter-clockwise
    M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
    
    # Calculate new image dimensions to avoid cropping
    # This is especially important for non-90-degree rotations
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix to prevent cropping
    M[0, 2] += (new_w / 2) - (w / 2)
    M[1, 2] += (new_h / 2) - (h / 2)
    
    # Perform the rotation with border replication to avoid black borders
    rotated = cv2.warpAffine(img, M, (new_w, new_h), flags=cv2.INTER_CUBIC, 
                            borderMode=cv2.BORDER_REPLICATE)
    return rotated


def _read_serials_from_image(
    img: np.ndarray,
    min_confidence: float = 0.0,
    low_text: float = 0.3,
    text_threshold: float = 0.7,
    mag_ratio: float = 1.0,
) -> List[Tuple[str, float]]:
    """Extract serial numbers from a processed image.
    
    Args:
        img: Preprocessed image
        min_confidence: Minimum confidence threshold
        low_text: EasyOCR low_text parameter
        text_threshold: EasyOCR text_threshold parameter
        mag_ratio: EasyOCR magnification ratio
        
    Returns:
        List of (serial, confidence) tuples
    """
    reader = _get_reader()
    
    # Use allowlist for alphanumeric characters only
    allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    
    # Run OCR
    results = reader.readtext(
        img,
        detail=1,
        paragraph=False,
        decoder="greedy",
        beamWidth=5,
        batch_size=8,
        allowlist=allowlist,
        low_text=low_text,
        text_threshold=text_threshold,
        mag_ratio=mag_ratio,
    )
    
    serials: List[Tuple[str, float]] = []
    for box, text, conf in results:
        # Skip if below confidence threshold
        if conf < min_confidence:
            continue
        
        # Clean up text
        clean = "".join(c for c in text if c.isalnum()).upper()
        if len(clean) < 8:  # Skip very short strings
            continue
        
        # Check if it looks like an Apple serial
        if is_valid_apple_serial(clean):
            serials.append((clean, conf))
        else:
            # Try expanding ambiguous characters
            variants = _expand_ambiguous(clean)
            for v in variants:
                if is_valid_apple_serial(v):
                    serials.append((v, conf * 0.95))  # Slightly reduce confidence for variants
                    break
    
    return serials


def _find_rois_by_projection(
    img: np.ndarray, top_k: int = 2, pad: int = 5, adaptive_pad: bool = False
) -> List[Tuple[int, int]]:
    """Find regions of interest by row projection.
    
    Args:
        img: Grayscale image
        top_k: Number of ROIs to return
        pad: Padding around ROIs
        adaptive_pad: Whether to use adaptive padding based on ROI height
        
    Returns:
        List of (y0, y1) tuples for ROI bands
    """
    h, w = img.shape[:2]
    
    # Calculate horizontal projection (sum of pixel values per row)
    if img.ndim > 2:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Binarize to emphasize text
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate row projection
    row_projection = np.sum(binary, axis=1)
    
    # Normalize to 0-1 range
    if np.max(row_projection) > 0:
        row_projection = row_projection / np.max(row_projection)
    
    # Find peaks (text-dense rows)
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(row_projection, height=0.3, distance=20)
    
    # Group nearby peaks into bands
    bands = []
    current_band = []
    
    for peak in peaks:
        if not current_band or peak - current_band[-1] < 20:  # If peaks are close, group them
            current_band.append(peak)
        else:
            if current_band:  # Save the previous band
                bands.append((min(current_band), max(current_band)))
            current_band = [peak]
    
    # Add the last band if it exists
    if current_band:
        bands.append((min(current_band), max(current_band)))
    
    # Sort bands by projection strength (sum of values in band)
    band_scores = []
    for y0, y1 in bands:
        score = np.sum(row_projection[y0:y1+1])
        band_scores.append((y0, y1, score))
    
    # Sort by score (highest first)
    band_scores.sort(key=lambda x: x[2], reverse=True)
    
    # Take top K bands and add padding
    result = []
    for y0, y1, _ in band_scores[:top_k]:
        # Calculate adaptive padding if requested
        if adaptive_pad:
            band_height = y1 - y0
            pad_value = min(pad * 2, max(pad, int(band_height * 0.5)))
        else:
            pad_value = pad
        
        # Apply padding with bounds checking
        y0_padded = max(0, y0 - pad_value)
        y1_padded = min(h - 1, y1 + pad_value)
        
        result.append((y0_padded, y1_padded))
    
    return result


def _keyword_guided_boxes(
    image_bytes: bytes, 
    processed_shape: Tuple[int, int], 
    keyword: str = "SERIAL",
    expansion_factor: float = 2.5,
) -> List[Tuple[int, int, int, int]]:
    """
    Find regions near a keyword (e.g., "Serial") to focus OCR.
    
    Args:
        image_bytes: Raw image bytes
        processed_shape: Shape of the processed image (h, w)
        keyword: Keyword to search for (e.g., "SERIAL")
        expansion_factor: How much to expand the region around the keyword
        
    Returns:
        List of (y0, y1, x0, x1) tuples for regions around keywords
    """
    # Decode the image
    file_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        return []
    
    # Convert to RGB for EasyOCR
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Get the reader
    reader = _get_reader()
    
    # Run OCR with loose settings to find keywords
    results = reader.readtext(
        rgb,
        detail=1,
        paragraph=False,
        decoder="greedy",
        beamWidth=5,
        batch_size=8,
        low_text=0.1,  # Very low threshold to catch more text
        text_threshold=0.3,
        mag_ratio=1.0,
    )
    
    # Find keyword matches
    boxes = []
    keyword_upper = keyword.upper()
    
    for box, text, conf in results:
        # Check if text contains the keyword (case insensitive)
        if keyword_upper in text.upper() and conf > 0.2:
            # Extract coordinates
            points = np.array(box)
            x0, y0 = np.min(points, axis=0)
            x1, y1 = np.max(points, axis=0)
            
            # Convert to integers
            x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
            
            # Expand the region
            h, w = processed_shape
            width = x1 - x0
            height = y1 - y0
            
            # Expand more horizontally than vertically
            x_expand = int(width * expansion_factor)
            y_expand = int(height * 1.5)
            
            # Apply expansion with bounds checking
            x0_exp = max(0, x0 - x_expand)
            x1_exp = min(w - 1, x1 + x_expand)
            y0_exp = max(0, y0 - y_expand)
            y1_exp = min(h - 1, y1 + y_expand)
            
            boxes.append((y0_exp, y1_exp, x0_exp, x1_exp))
    
    return boxes


def extract_serials(
    image_bytes: bytes,
    min_confidence: float = 0.0,
    debug_save_path: Optional[str] = None,
    try_rotations: Iterable[float] = (0, 90, 180, 270),  # Changed from int to float
    low_text: float = 0.3,
    text_threshold: float = 0.6,
    roi: bool = False,
    roi_top_k: int = 3,  # Increased from 2 to 3
    roi_pad: int = 8,
    adaptive_pad: bool = True,  # New parameter for adaptive padding
    mag_ratio: float = 1.0,  # New parameter for EasyOCR magnification ratio
    fine_rotation: bool = False,  # New parameter to enable fine-grained rotations
    keyword_crop: bool = False,  # New: crop near keyword (e.g., 'Serial')
    keyword: str = "SERIAL",
    zoom_strips: int = 0,  # New: split image into N horizontal strips to zoom when text is far
    **preprocess_kwargs,
) -> List[Tuple[str, float]]:
    """Extract serial numbers from an image with enhanced options.
    
    Args:
        image_bytes: Raw image bytes
        min_confidence: Minimum confidence threshold for results
        debug_save_path: Path to save debug image
        try_rotations: Rotation angles to try (TTA)
        low_text: EasyOCR low_text parameter
        text_threshold: EasyOCR text_threshold parameter
        roi: Whether to use ROI detection
        roi_top_k: Number of ROIs to detect
        roi_pad: ROI padding
        adaptive_pad: Whether to use adaptive ROI padding
        mag_ratio: EasyOCR magnification ratio
        fine_rotation: Whether to add fine-grained rotation angles (±15°, ±30°)
        **preprocess_kwargs: Additional preprocessing parameters
        
    Returns:
        List of (serial, confidence) tuples
    """
    # Generate a unique image ID for logging
    image_id = f"img_{time.time():.6f}"
    
    # Create timers for each stage
    with Timer("preprocess") as preproc_timer:
        processed = preprocess_image(image_bytes, debug_save_path=debug_save_path, **preprocess_kwargs)

    # Build working images (RGB and inverse)
    if processed.ndim == 2:
        rgb_full = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        rgb_full_inv = cv2.cvtColor(255 - processed, cv2.COLOR_GRAY2RGB)
        band_source = processed
    else:
        rgb_full = processed
        rgb_full_inv = 255 - processed
        band_source = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

    imgs_to_scan: List[np.ndarray] = []
    inv_to_scan: List[np.ndarray] = []

    # Track ROI detection timing
    with Timer("roi_detection") as roi_timer:
        if roi:
            for (y0, y1) in _find_rois_by_projection(band_source, top_k=roi_top_k, pad=roi_pad, adaptive_pad=adaptive_pad):
                imgs_to_scan.append(rgb_full[y0:y1, :])
                inv_to_scan.append(rgb_full_inv[y0:y1, :])
            # Fallback to full frame if no ROI found
            if not imgs_to_scan:
                imgs_to_scan = [rgb_full]
                inv_to_scan = [rgb_full_inv]
        else:
            # Keyword-guided crops (highest priority)
            if keyword_crop:
                boxes = _keyword_guided_boxes(image_bytes, processed_shape=band_source.shape[:2], keyword=keyword)
                for (ky0, ky1, kx0, kx1) in boxes:
                    imgs_to_scan.append(rgb_full[ky0:ky1, kx0:kx1])
                    inv_to_scan.append(rgb_full_inv[ky0:ky1, kx0:kx1])
            # If zoom_strips requested, split into horizontal bands to zoom into likely text rows
            if isinstance(zoom_strips, int) and zoom_strips and zoom_strips > 1:
                h, w = band_source.shape[:2]
                strip_h = max(1, h // zoom_strips)
                for i in range(zoom_strips):
                    y0 = i * strip_h
                    y1 = h if i == zoom_strips - 1 else min(h, y0 + strip_h)
                    if y1 - y0 < max(8, h // 40):
                        continue
                    imgs_to_scan.append(rgb_full[y0:y1, :])
                    inv_to_scan.append(rgb_full_inv[y0:y1, :])
                # Fallback to full frame as well
                if not imgs_to_scan:
                    imgs_to_scan = [rgb_full]
                    inv_to_scan = [rgb_full_inv]
                else:
                    imgs_to_scan.append(rgb_full)
                    inv_to_scan.append(rgb_full_inv)
            else:
                imgs_to_scan = [rgb_full]
                inv_to_scan = [rgb_full_inv]

    # Track OCR detection timing
    all_serials: List[Tuple[str, float]] = []
    with Timer("ocr_detection") as ocr_timer:
        for rgb, rgb_inv in zip(imgs_to_scan, inv_to_scan):
            # Process with standard rotations
            angles_to_try = list(try_rotations)
            
            # Add fine-grained rotations if requested
            if fine_rotation:
                # Add small angle variations around each main rotation
                fine_angles = []
                for base_angle in try_rotations:
                    # Add ±15° and ±30° around each main angle
                    fine_angles.extend([
                        base_angle - 30, base_angle - 15,
                        base_angle + 15, base_angle + 30
                    ])
                angles_to_try.extend(fine_angles)
            
            # Process each rotation angle
            for ang in angles_to_try:
                rimg = _rotate_image(rgb, ang)
                all_serials.extend(
                    _read_serials_from_image(
                        rimg, 
                        min_confidence=min_confidence, 
                        low_text=low_text, 
                        text_threshold=text_threshold,
                        mag_ratio=mag_ratio
                    )
                )
                rimg_inv = _rotate_image(rgb_inv, ang)
                all_serials.extend(
                    _read_serials_from_image(
                        rimg_inv, 
                        min_confidence=min_confidence, 
                        low_text=low_text, 
                        text_threshold=text_threshold,
                        mag_ratio=mag_ratio
                    )
                )

    # Track validation timing
    with Timer("validation") as validation_timer:
        # Aggregate by normalized (ambiguous collapsed) key
        score_by_norm: dict[str, float] = {}
        best_variant_by_norm: dict[str, Tuple[str, float]] = {}
        for s, c in all_serials:
            norm = _normalize_ambiguous(s)
            score_by_norm[norm] = score_by_norm.get(norm, 0.0) + c
            if norm not in best_variant_by_norm or c > best_variant_by_norm[norm][1]:
                best_variant_by_norm[norm] = (s, c)

        # Return best variants ordered by aggregated score
        ordered_norms = sorted(score_by_norm.items(), key=lambda kv: kv[1], reverse=True)
        merged: List[Tuple[str, float]] = [(best_variant_by_norm[n][0], best_variant_by_norm[n][1]) for n, _ in ordered_norms]

    # Calculate total time
    total_time = preproc_timer.elapsed + roi_timer.elapsed + ocr_timer.elapsed + validation_timer.elapsed
    
    # Log traditional message for backward compatibility
    logger.info(
        "ocr: processed=%d regions, time_preproc=%.3fs, time_ocr=%.3fs, params={low_text=%.2f,text_threshold=%.2f,mag_ratio=%.2f,roi=%s,zoom_strips=%d}",
        len(imgs_to_scan),
        preproc_timer.elapsed,
        ocr_timer.elapsed,
        low_text,
        text_threshold,
        mag_ratio,
        str(roi),
        int(zoom_strips or 0),
    )
    
    # Log structured timing information
    log_ocr_timing(
        image_id=image_id,
        total_time=total_time,
        preprocessing_time=preproc_timer.elapsed,
        detection_time=ocr_timer.elapsed,
        validation_time=validation_timer.elapsed,
        serials_found=len(merged),
        top_confidence=merged[0][1] if merged else None,
        additional_data={
            "params": {
                "low_text": low_text,
                "text_threshold": text_threshold,
                "mag_ratio": mag_ratio,
                "roi": roi,
                "roi_top_k": roi_top_k,
                "zoom_strips": zoom_strips,
                "keyword_crop": keyword_crop,
                "fine_rotation": fine_rotation,
                "rotations_count": len(list(try_rotations)),
                "regions_count": len(imgs_to_scan),
            }
        }
    )
    
    # Log debug asset if saved
    if debug_save_path:
        log_debug_asset(
            image_id=image_id,
            asset_type="preprocessed",
            asset_path=debug_save_path,
            related_serial=merged[0][0] if merged else None,
            confidence=merged[0][1] if merged else None,
        )
    
    # Log detection miss if no serials found
    if not merged:
        params = {
            "low_text": low_text,
            "text_threshold": text_threshold,
            "mag_ratio": mag_ratio,
            "roi": roi,
            "roi_top_k": roi_top_k,
            "zoom_strips": zoom_strips,
            "keyword_crop": keyword_crop,
            "fine_rotation": fine_rotation,
        }
        log_detection_miss(
            image_id=image_id,
            params=params,
            debug_path=debug_save_path,
        )
    
    return merged