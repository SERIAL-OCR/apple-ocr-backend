from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Set, Dict, Any
import logging
import os
import time

import cv2
import numpy as np
import easyocr
import gc

from app.utils.validation import is_valid_apple_serial, validate_apple_serial_extended
from app.pipeline.tesseract_adapter import extract_serials_with_tesseract, TESSERACT_AVAILABLE
from app.pipeline.yolo_detector import detect_serial_regions
from app.config import OCR_SETTINGS


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
            
            # Configure GPU memory usage if available
            if use_gpu and torch.cuda.is_available():
                # Set memory fraction to use
                torch.cuda.set_per_process_memory_fraction(0.8)  # Use up to 80% of GPU memory
                
                # Enable memory caching for faster allocation
                torch.cuda.empty_cache()
                
                logger.info(f"[GPU] Configured memory fraction: 0.8, device: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            gpu_info = f"torch_error: {str(e)}"
            
        logger.info(f"[EasyOCR] Initializing Reader(langs={languages}, gpu={use_gpu}) [{gpu_info}]")
        _reader = easyocr.Reader(languages, gpu=use_gpu)
    return _reader


def _morphological_refine(binary_img: np.ndarray, k: int = 2) -> np.ndarray:
    """Apply morphological operations to clean up binary image."""
    # First close to connect nearby components
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (k+1, k))
    closed = cv2.morphologyEx(binary_img, cv2.MORPH_CLOSE, kernel_close, iterations=1)
    
    # Then open to remove small noise
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)
    
    return opened


def _detect_glare_regions(image: np.ndarray, threshold: int = 220) -> np.ndarray:
    """Detect regions with glare in the image.
    
    Args:
        image: Grayscale image
        threshold: Brightness threshold for glare detection
        
    Returns:
        Binary mask of glare regions
    """
    # Threshold to find very bright regions
    _, glare_mask = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    
    # Apply morphological operations to clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_CLOSE, kernel)
    glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_OPEN, kernel)
    
    return glare_mask


def _reduce_glare(image: np.ndarray, method: str = "tophat", multi_scale: bool = False) -> np.ndarray:
    """Reduce glare and improve illumination uniformity.
    
    Args:
        image: Grayscale image
        method: "tophat" for morphological top-hat, "division" for background division,
                "adaptive" to choose automatically based on image statistics,
                "multi" for multi-scale glare reduction
        multi_scale: Whether to use multi-scale processing for better glare handling
    
    Returns:
        Image with reduced glare
    """
    # Auto-select method if "adaptive" is specified
    if method == "adaptive":
        # Calculate image statistics
        mean_val = np.mean(image)
        std_val = np.std(image)
        
        # Check for glare regions
        glare_mask = _detect_glare_regions(image)
        glare_ratio = np.sum(glare_mask > 0) / (image.shape[0] * image.shape[1])
        
        # If significant glare detected, use multi-scale approach
        if glare_ratio > 0.05:
            method = "multi"
        # If high mean and low std, likely has uniform glare - use division
        elif mean_val > 180 and std_val < 50:
            method = "division"
        # If medium brightness with higher contrast, likely has spotty glare - use tophat
        else:
            method = "tophat"
        
        logger.debug(f"Auto-selected glare reduction: {method} (mean={mean_val:.1f}, std={std_val:.1f}, glare_ratio={glare_ratio:.3f})")
    
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
    elif method == "multi" or multi_scale:
        # Multi-scale glare reduction
        # 1. Detect glare regions
        glare_mask = _detect_glare_regions(image)
        
        # 2. Apply local contrast enhancement to glare regions
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        
        # 3. Apply division method to glare regions
        background = cv2.GaussianBlur(image, (51, 51), 0)
        divided = cv2.divide(image, background, scale=255)
        
        # 4. Apply tophat method to the entire image
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
        tophat = cv2.morphologyEx(image, cv2.MORPH_TOPHAT, kernel)
        tophat_result = cv2.add(image, tophat)
        
        # 5. Combine results based on glare mask
        # For severe glare areas, use division method
        # For moderate glare, use tophat
        # For non-glare areas, use enhanced original
        result = np.zeros_like(image)
        severe_glare = _detect_glare_regions(image, threshold=240)
        moderate_glare = cv2.subtract(glare_mask, severe_glare)
        
        # Combine using masks
        result = np.where(severe_glare > 0, divided, result)
        result = np.where(moderate_glare > 0, tophat_result, result)
        result = np.where(glare_mask == 0, enhanced, result)
        
        # Final smoothing to avoid artifacts at boundaries
        result = cv2.GaussianBlur(result, (3, 3), 0)
    else:
        result = image
    
    return result


def _sharpen_image(image: np.ndarray, amount: float = 1.5) -> np.ndarray:
    """Apply sharpening to the image to enhance text edges."""
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


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
    glare_reduction: Optional[str] = None,  # None, "tophat", "division", or "adaptive"
    sharpen: bool = True,  # Whether to apply sharpening
    debug_save_path: Optional[str] = None,
    debug_steps: bool = False,  # Save intermediate steps for debugging
) -> np.ndarray:
    """Preprocess image for OCR with enhanced options."""
    file_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")
    
    # Create debug directory if needed
    debug_dir = None
    if debug_steps and debug_save_path:
        debug_dir = os.path.join(os.path.dirname(debug_save_path), "steps")
        os.makedirs(debug_dir, exist_ok=True)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "01_gray.png"), gray)
    
    # Apply glare reduction if requested
    if glare_reduction:
        gray = _reduce_glare(gray, method=glare_reduction, multi_scale=(glare_reduction == "multi"))
        if debug_dir:
            cv2.imwrite(os.path.join(debug_dir, "02_glare_reduced.png"), gray)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    enhanced = clahe.apply(gray)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "03_clahe.png"), enhanced)
    
    # Apply bilateral filter to smooth while preserving edges
    filtered = cv2.bilateralFilter(
        enhanced, d=bilateral_d, sigmaColor=bilateral_sigma_color, sigmaSpace=bilateral_sigma_space
    )
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, "04_bilateral.png"), filtered)
    
    # Apply sharpening if requested
    if sharpen:
        filtered = _sharpen_image(filtered, amount=1.5)
        if debug_dir:
            cv2.imwrite(os.path.join(debug_dir, "05_sharpened.png"), filtered)
    
    # Process based on mode
    if mode == "gray":
        out = filtered
    else:
        # Apply adaptive thresholding for binary mode
        th = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, thresh_block_size, thresh_C
        )
        if debug_dir:
            cv2.imwrite(os.path.join(debug_dir, "06_threshold.png"), th)
        
        # Apply morphological operations to clean up binary image
        out = _morphological_refine(th, k=morph_kernel)
        if debug_dir:
            cv2.imwrite(os.path.join(debug_dir, "07_morphology.png"), out)
    
    # Upscale the image if requested
    if upscale_scale and upscale_scale != 1.0:
        out = cv2.resize(out, None, fx=upscale_scale, fy=upscale_scale, interpolation=cv2.INTER_CUBIC)
        if debug_dir:
            cv2.imwrite(os.path.join(debug_dir, "08_upscaled.png"), out)
    
    # Save final preprocessed image if requested
    if debug_save_path:
        cv2.imwrite(debug_save_path, out)
    
    return out


_AMBIGUOUS_MAP: Dict[str, str] = {
    "O": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "Q": "0",
    "G": "6",
    "D": "0",  # Sometimes D is confused with 0
    "T": "7",  # Sometimes T is confused with 7
}


def _expand_ambiguous(text: str, position_aware: bool = False) -> Set[str]:
    """Generate all possible variants by replacing ambiguous characters.
    
    Args:
        text: Text to expand
        position_aware: Whether to use position-specific rules for Apple serials
        
    Returns:
        Set of possible variants
    """
    variants: Set[str] = {text}
    for idx, ch in enumerate(text):
        # Skip certain positions if using position-aware rules
        if position_aware:
            # First 3 chars more likely to be letters
            if idx < 3 and ch in ('O', 'I'):
                continue
            # Last 4 chars more likely to be digits
            if idx >= 8 and ch in ('G', 'B', 'D'):
                continue
        
        rep = _AMBIGUOUS_MAP.get(ch)
        if rep:
            for v in list(variants):
                variants.add(v[:idx] + rep + v[idx + 1:])
    return variants


def _normalize_ambiguous(text: str, position_aware: bool = False) -> str:
    """Normalize text by replacing ambiguous characters with their canonical form.
    
    Args:
        text: Text to normalize
        position_aware: Whether to use position-specific rules for Apple serials
        
    Returns:
        Normalized text with ambiguous characters replaced
    """
    up = text.strip().upper()
    result = ""
    
    for i, char in enumerate(up):
        if position_aware:
            # Apply position-specific rules for Apple serials
            if char == 'G' and i >= 8:  # Last 4 chars more likely to be digits
                result += '6'
            elif char == 'O' and i < 3:  # First 3 chars more likely to be letters
                result += 'O'
            elif char == 'I' and i < 3:  # First 3 chars more likely to be letters
                result += 'I'
            elif char == 'B' and i >= 8:  # Last 4 chars more likely to be digits
                result += '8'
            elif char == 'D' and i >= 8:  # Last 4 chars more likely to be digits
                result += '0'
            else:
                result += _AMBIGUOUS_MAP.get(char, char)
        else:
            result += _AMBIGUOUS_MAP.get(char, char)
    
    return result


def _detect_text_orientation(img: np.ndarray) -> int:
    """Detect the likely orientation of text in the image.
    
    This function uses horizontal and vertical projections to determine
    if text is likely horizontal, vertical, or upside down.
    
    Args:
        img: Input image (grayscale)
        
    Returns:
        Likely rotation angle (0, 90, 180, or 270)
    """
    # Ensure grayscale
    if len(img.shape) > 2:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Apply threshold to get binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate horizontal and vertical projections
    h_proj = np.sum(binary, axis=1)
    v_proj = np.sum(binary, axis=0)
    
    # Normalize projections
    h_proj = h_proj / np.max(h_proj) if np.max(h_proj) > 0 else h_proj
    v_proj = v_proj / np.max(v_proj) if np.max(v_proj) > 0 else v_proj
    
    # Calculate variation in projections
    h_var = np.var(h_proj)
    v_var = np.var(v_proj)
    
    # Calculate projection peaks and distances
    h_peaks = np.where(h_proj > 0.5)[0]
    v_peaks = np.where(v_proj > 0.5)[0]
    
    h_peak_distances = np.diff(h_peaks) if len(h_peaks) > 1 else [0]
    v_peak_distances = np.diff(v_peaks) if len(v_peaks) > 1 else [0]
    
    h_mean_distance = np.mean(h_peak_distances) if len(h_peak_distances) > 0 else 0
    v_mean_distance = np.mean(v_peak_distances) if len(v_peak_distances) > 0 else 0
    
    # Check if text is more likely horizontal or vertical
    if h_var > v_var * 1.5 and h_mean_distance > v_mean_distance * 0.8:
        # Text is likely horizontal (0 or 180 degrees)
        # Check if it's upside down by analyzing top vs bottom half
        top_half = np.sum(binary[:binary.shape[0]//2, :])
        bottom_half = np.sum(binary[binary.shape[0]//2:, :])
        
        if top_half > bottom_half * 1.2:
            return 180  # Text is likely upside down
        else:
            return 0    # Text is likely right-side up
    elif v_var > h_var * 1.5 and v_mean_distance > h_mean_distance * 0.8:
        # Text is likely vertical (90 or 270 degrees)
        # Check if it's 90 or 270 by analyzing left vs right half
        left_half = np.sum(binary[:, :binary.shape[1]//2])
        right_half = np.sum(binary[:, binary.shape[1]//2:])
        
        if left_half > right_half * 1.2:
            return 90   # Text is likely rotated 90 degrees
        else:
            return 270  # Text is likely rotated 270 degrees
    else:
        # Can't determine orientation confidently, default to 0
        return 0


def _get_smart_rotation_angles(img: np.ndarray, fine_rotation: bool = False) -> List[int]:
    """Determine the best rotation angles to try based on image analysis.
    
    Args:
        img: Input image
        fine_rotation: Whether to include fine rotation angles
        
    Returns:
        List of rotation angles to try
    """
    # Detect the primary orientation
    primary_angle = _detect_text_orientation(img)
    
    # Always include the detected primary angle
    angles = [primary_angle]
    
    # Add the opposite orientation as a fallback
    opposite_angle = (primary_angle + 180) % 360
    angles.append(opposite_angle)
    
    # If the orientation detection isn't confident between horizontal/vertical,
    # add the other orientations
    if primary_angle in [0, 180]:
        angles.extend([90, 270])
    else:  # primary_angle in [90, 270]
        angles.extend([0, 180])
    
    # Add fine rotation angles if requested
    if fine_rotation:
        fine_angles = []
        for angle in angles[:2]:  # Only add fine rotations for primary and opposite angles
            fine_angles.extend([angle - 15, angle - 7, angle + 7, angle + 15])
        angles.extend(fine_angles)
    
    # Remove duplicates and sort
    angles = sorted(list(set(angles)))
    
    return angles


def _rotate_image(img: np.ndarray, angle: int) -> np.ndarray:
    """Rotate image by specified angle."""
    if angle % 360 == 0:
        return img
    if angle % 180 == 0:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle % 270 == 0:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if angle % 90 == 0:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    
    # For arbitrary angles
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR)


_ALLOWED = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _read_serials_from_image(
    img: np.ndarray,
    min_confidence: float,
    low_text: float = 0.3,
    text_threshold: float = 0.6,
    mag_ratio: float = 1.0,  # EasyOCR magnification ratio
) -> List[Tuple[str, float]]:
    """Extract serial numbers from an image using EasyOCR."""
    # Limit image size to prevent OOM errors
    max_side = 1024
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h} to prevent OOM")
    
    reader = _get_reader()
    
    try:
        # Try to use mixed precision if available
        import torch  # type: ignore
        if hasattr(torch, 'amp') and OCR_SETTINGS["use_gpu"]:
            # Use the updated syntax for autocast
            with torch.amp.autocast(device_type='cuda'):
                results = reader.readtext(
                    img,
                    detail=1,
                    paragraph=False,
                    allowlist=_ALLOWED,
                    low_text=low_text,
                    text_threshold=text_threshold,
                    mag_ratio=mag_ratio,
                )
        else:
            results = reader.readtext(
                img,
                detail=1,
                paragraph=False,
                allowlist=_ALLOWED,
                low_text=low_text,
                text_threshold=text_threshold,
                mag_ratio=mag_ratio,
            )
            
        # Clear GPU cache after inference if using GPU
        if OCR_SETTINGS["use_gpu"]:
            torch.cuda.empty_cache()
            gc.collect()  # Also run garbage collection
            
    except Exception as e:
        logger.error(f"Error during OCR inference: {str(e)}")
        # Fallback to CPU if GPU fails
        if OCR_SETTINGS["use_gpu"]:
            logger.warning("Falling back to CPU inference after GPU error")
            global _reader
            _reader = None  # Force reader re-initialization with CPU
            OCR_SETTINGS["use_gpu"] = False
            reader = _get_reader()
            results = reader.readtext(
                img,
                detail=1,
                paragraph=False,
                allowlist=_ALLOWED,
                low_text=low_text,
                text_threshold=text_threshold,
                mag_ratio=mag_ratio,
            )
        else:
            # If already on CPU, re-raise the exception
            raise
    
    serials: List[Tuple[str, float]] = []
    for bbox, text, confidence in results:
        base = text.strip().upper().replace(" ", "")
        candidates = _expand_ambiguous(base, position_aware=True)
        for c in candidates:
            if is_valid_apple_serial(c) and float(confidence) >= min_confidence:
                serials.append((c, float(confidence)))
    
    return serials


def _find_rois_by_projection(
    img_gray_or_bin: np.ndarray, 
    top_k: int = 2, 
    pad: int = 8,
    adaptive_pad: bool = True,
) -> List[Tuple[int, int]]:
    """Find regions of interest by row projection with adaptive padding."""
    # Expect single channel image
    img = img_gray_or_bin
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = img.shape[:2]

    # Compute ink density per row
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)
    ink = 255 - img  # brighter means more strokes
    proj = ink.sum(axis=1).astype(np.float32)
    
    # Smooth projection
    proj = cv2.GaussianBlur(proj.reshape(-1, 1), (1, 9), 0).reshape(-1)

    # Dynamic threshold based on projection statistics
    mean_proj = np.mean(proj)
    max_proj = np.max(proj)
    thr = max(mean_proj * 1.5, max_proj * 0.3)
    
    mask = (proj >= thr).astype(np.uint8)

    rois: List[Tuple[int, int]] = []
    start = None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        if (not v or i == len(mask) - 1) and start is not None:
            end = i if not v else i
            # Filter tiny bands
            if end - start > max(8, h // 20):
                # Calculate adaptive padding based on ROI height
                if adaptive_pad:
                    roi_height = end - start
                    # Larger padding for smaller ROIs, smaller padding for larger ROIs
                    adaptive_pad_val = min(int(roi_height * 0.5), pad * 2)
                    y0 = max(0, start - adaptive_pad_val)
                    y1 = min(h, end + adaptive_pad_val)
                else:
                    y0 = max(0, start - pad)
                    y1 = min(h, end + pad)
                rois.append((y0, y1))
            start = None

    # Sort by projected energy
    rois = sorted(rois, key=lambda yy: proj[yy[0]:yy[1]].sum(), reverse=True)
    return rois[:top_k]


def progressive_process(
    image_bytes: bytes,
    min_confidence: float = 0.0,
    early_stop_confidence: float = 0.95,
    debug_save_path: Optional[str] = None,
    max_processing_time: float = 30.0,  # Maximum processing time in seconds
    debug_steps: bool = False,
    use_tesseract_fallback: bool = True,
    use_yolo_roi: bool = True,
) -> List[Tuple[str, float]]:
    """Process image with progressive complexity until good results are found.
    
    This function implements a multi-stage processing pipeline that starts with fast,
    simple processing and only moves to more complex (and slower) processing if needed.
    
    Args:
        image_bytes: Raw image bytes
        min_confidence: Minimum confidence threshold for results
        early_stop_confidence: Confidence threshold for early stopping
        debug_save_path: Path to save debug images
        max_processing_time: Maximum processing time in seconds
        debug_steps: Whether to save intermediate processing steps
        
    Returns:
        List of (serial, confidence) tuples
    """
    start_time = time.time()
    
    # Try YOLO ROI detection first if enabled
    roi_crops = []
    if use_yolo_roi:
        try:
            logger.info("[Progressive] Using YOLO ROI detector")
            roi_crops = detect_serial_regions(image_bytes, padding=0.15)
            
            if roi_crops:
                logger.info(f"[Progressive] YOLO detected {len(roi_crops)} ROI regions")
                
                # Save debug images if requested
                if debug_save_path and debug_steps:
                    debug_dir = os.path.dirname(debug_save_path)
                    for i, crop in enumerate(roi_crops):
                        crop_path = os.path.join(debug_dir, f"yolo_roi_{i}.png")
                        cv2.imwrite(crop_path, crop)
        except Exception as e:
            logger.error(f"[Progressive] Error in YOLO ROI detection: {str(e)}")
            roi_crops = []
    
    # Stage 1: Fast processing (grayscale, basic preprocessing, minimal rotations)
    logger.info("[Progressive] Stage 1: Fast processing")
    # If we have YOLO ROI crops, process them first
    results = []
    if roi_crops:
        for i, crop in enumerate(roi_crops):
            # Convert crop to bytes
            _, crop_bytes = cv2.imencode(".png", crop)
            crop_bytes = crop_bytes.tobytes()
            
            # Process the crop with optimized settings
            crop_results = extract_serials(
                crop_bytes,
                min_confidence=min_confidence,
                early_stop_confidence=early_stop_confidence,
                enable_early_stop=True,
                smart_rotation=True,
                roi=False,  # No need for ROI detection on crops
                fine_rotation=False,
                upscale_scale=2.5,  # Slightly higher upscale for crops
                mode="gray",
                glare_reduction="adaptive",
                debug_save_path=debug_save_path + f".yolo_crop_{i}.png" if debug_save_path else None,
                debug_steps=debug_steps,
            )
            
            # Add results
            results.extend(crop_results)
        
        # If we got good results from YOLO crops, return them
        if results and results[0][1] >= 0.8:
            logger.info(f"[Progressive] YOLO ROI success: {results[0][0]} ({results[0][1]:.3f})")
            return sorted(results, key=lambda x: x[1], reverse=True)
    
    # If YOLO didn't give good results or wasn't used, continue with normal pipeline
    stage1_results = extract_serials(
        image_bytes,
        min_confidence=min_confidence,
        early_stop_confidence=early_stop_confidence,
        enable_early_stop=True,
        smart_rotation=True,
        roi=True,
        roi_top_k=2,
        fine_rotation=False,
        upscale_scale=2.0,
        mode="gray",
        glare_reduction=None,
        debug_save_path=debug_save_path + ".stage1.png" if debug_save_path else None,
        debug_steps=debug_steps,
    )
    
    # Merge results
    results.extend(stage1_results)
    results = sorted(results, key=lambda x: x[1], reverse=True)
    
    # Check if we got good results
    if results and results[0][1] >= 0.8:
        logger.info(f"[Progressive] Stage 1 success: {results[0][0]} ({results[0][1]:.3f})")
        return results
    
    # Check if we're out of time
    if time.time() - start_time > max_processing_time:
        logger.warning(f"[Progressive] Time limit reached after Stage 1: {time.time() - start_time:.2f}s")
        return results if results else []
    
    # Stage 2: Medium processing (more rotations, better preprocessing)
    logger.info("[Progressive] Stage 2: Medium processing")
    results = extract_serials(
        image_bytes,
        min_confidence=min_confidence,
        early_stop_confidence=early_stop_confidence,
        enable_early_stop=True,
        smart_rotation=True,
        roi=True,
        roi_top_k=3,
        adaptive_pad=True,
        fine_rotation=False,
        upscale_scale=3.0,
        mode="binary",
        glare_reduction="adaptive",
        debug_save_path=debug_save_path + ".stage2.png" if debug_save_path else None,
        debug_steps=debug_steps,
    )
    
    # Check if we got good results
    if results and results[0][1] >= 0.7:
        logger.info(f"[Progressive] Stage 2 success: {results[0][0]} ({results[0][1]:.3f})")
        return results
    
    # Check if we're out of time
    if time.time() - start_time > max_processing_time:
        logger.warning(f"[Progressive] Time limit reached after Stage 2: {time.time() - start_time:.2f}s")
        return results if results else []
    
    # Stage 3: Full processing (all optimizations)
    logger.info("[Progressive] Stage 3: Full processing")
    results = extract_serials(
        image_bytes,
        min_confidence=min_confidence,
        early_stop_confidence=early_stop_confidence,
        enable_early_stop=True,
        smart_rotation=True,
        roi=True,
        roi_top_k=3,
        adaptive_pad=True,
        fine_rotation=True,
        upscale_scale=4.0,
        mode="binary",
        glare_reduction="multi",
        sharpen=True,
        low_text=0.12,  # More permissive
        text_threshold=0.3,  # More permissive
        mag_ratio=1.8,  # Higher magnification
        debug_save_path=debug_save_path + ".stage3.png" if debug_save_path else None,
        debug_steps=debug_steps,
    )
    
    # Check if we got good results
    if results and results[0][1] >= 0.7:
        logger.info(f"[Progressive] Stage 3 success: {results[0][0]} ({results[0][1]:.3f})")
        return results
    
    # Check if we're out of time
    if time.time() - start_time > max_processing_time:
        logger.warning(f"[Progressive] Time limit reached after Stage 3: {time.time() - start_time:.2f}s")
        return results if results else []
    
    # Stage 4: Tesseract fallback (if available and enabled)
    if use_tesseract_fallback and TESSERACT_AVAILABLE:
        logger.info("[Progressive] Stage 4: Tesseract fallback")
        
        # Process the image for Tesseract
        processed = preprocess_image(
            image_bytes, 
            upscale_scale=3.0,  # Higher scale for Tesseract
            mode="binary",
            glare_reduction="multi",
            sharpen=True,
            debug_save_path=debug_save_path + ".stage4.png" if debug_save_path else None,
        )
        
        # Convert to RGB for Tesseract
        if processed.ndim == 2:
            rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        else:
            rgb = processed
            
        # Try with Tesseract
        tesseract_results = extract_serials_with_tesseract(
            rgb,
            min_confidence=min_confidence
        )
        
        # Merge results, prioritizing EasyOCR results
        if tesseract_results:
            # Add any new serials from Tesseract
            existing_serials = {r[0] for r in results}
            for serial, conf in tesseract_results:
                if serial not in existing_serials:
                    results.append((serial, conf))
            
            # Re-sort by confidence
            results = sorted(results, key=lambda x: x[1], reverse=True)
            
            logger.info(f"[Progressive] Tesseract found {len(tesseract_results)} candidates")
    
    logger.info(f"[Progressive] Total processing time: {time.time() - start_time:.2f}s")
    return results


def extract_serials(
    image_bytes: bytes,
    min_confidence: float = 0.0,
    early_stop_confidence: float = 0.95,
    enable_early_stop: bool = True,
    debug_save_path: Optional[str] = None,
    try_rotations: Optional[Iterable[int]] = None,
    smart_rotation: bool = True,
    fine_rotation: bool = False,
    low_text: float = 0.3,
    text_threshold: float = 0.6,
    roi: bool = False,
    roi_top_k: int = 2,
    roi_pad: int = 8,
    adaptive_pad: bool = True,
    mag_ratio: float = 1.0,
    sharpen: bool = True,
    debug_steps: bool = False,
    **preprocess_kwargs,
) -> List[Tuple[str, float]]:
    """Extract serial numbers from an image with enhanced options."""
    processed = preprocess_image(
        image_bytes, 
        debug_save_path=debug_save_path, 
        debug_steps=debug_steps,
        sharpen=sharpen,
        **preprocess_kwargs
    )

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

    if roi:
        for (y0, y1) in _find_rois_by_projection(band_source, top_k=roi_top_k, pad=roi_pad, adaptive_pad=adaptive_pad):
            imgs_to_scan.append(rgb_full[y0:y1, :])
            inv_to_scan.append(rgb_full_inv[y0:y1, :])
        
        # Fallback to full frame if no ROI found
        if not imgs_to_scan:
            imgs_to_scan = [rgb_full]
            inv_to_scan = [rgb_full_inv]
    else:
        imgs_to_scan = [rgb_full]
        inv_to_scan = [rgb_full_inv]

    all_serials: List[Tuple[str, float]] = []
    # Determine rotation angles to try
    if smart_rotation and try_rotations is None:
        # Use the first ROI or full image to determine orientation
        source_img = imgs_to_scan[0] if imgs_to_scan else rgb_full
        rotation_angles = _get_smart_rotation_angles(source_img, fine_rotation=fine_rotation)
        logger.debug(f"Smart rotation selected angles: {rotation_angles}")
    else:
        # Use specified rotations or default to all four orientations
        rotation_angles = list(try_rotations) if try_rotations is not None else [0, 90, 180, 270]
        
        # Add fine rotation angles if requested
        if fine_rotation and try_rotations is not None:
            fine_angles = []
            for angle in rotation_angles:
                fine_angles.extend([angle - 15, angle - 7, angle + 7, angle + 15])
            rotation_angles.extend(fine_angles)
            rotation_angles = sorted(list(set(rotation_angles)))
    
    for rgb, rgb_inv in zip(imgs_to_scan, inv_to_scan):
        for ang in rotation_angles:
            # Try normal image first
            rimg = _rotate_image(rgb, ang)
            results = _read_serials_from_image(
                rimg, 
                min_confidence=min_confidence, 
                low_text=low_text, 
                text_threshold=text_threshold,
                mag_ratio=mag_ratio,
            )
            all_serials.extend(results)
            
            # Early stopping if we found a high-confidence match
            if enable_early_stop and results:
                best_result = max(results, key=lambda x: x[1])
                if best_result[1] >= early_stop_confidence:
                    logger.info(f"Early stopping with high confidence match: {best_result[0]} ({best_result[1]:.3f})")
                    return [best_result]
            
            # Try inverted image
            rimg_inv = _rotate_image(rgb_inv, ang)
            results_inv = _read_serials_from_image(
                rimg_inv, 
                min_confidence=min_confidence, 
                low_text=low_text, 
                text_threshold=text_threshold,
                mag_ratio=mag_ratio,
            )
            all_serials.extend(results_inv)
            
            # Early stopping for inverted image too
            if enable_early_stop and results_inv:
                best_result_inv = max(results_inv, key=lambda x: x[1])
                if best_result_inv[1] >= early_stop_confidence:
                    logger.info(f"Early stopping with high confidence match (inverted): {best_result_inv[0]} ({best_result_inv[1]:.3f})")
                    return [best_result_inv]

    # Aggregate by normalized (ambiguous collapsed) key
    score_by_norm: Dict[str, float] = {}
    best_variant_by_norm: Dict[str, Tuple[str, float]] = {}
    for s, c in all_serials:
        norm = _normalize_ambiguous(s, position_aware=True)
        score_by_norm[norm] = score_by_norm.get(norm, 0.0) + c
        if norm not in best_variant_by_norm or c > best_variant_by_norm[norm][1]:
            best_variant_by_norm[norm] = (s, c)

    # Return best variants ordered by aggregated score
    ordered_norms = sorted(score_by_norm.items(), key=lambda kv: kv[1], reverse=True)
    merged: List[Tuple[str, float]] = [(best_variant_by_norm[n][0], best_variant_by_norm[n][1]) for n, _ in ordered_norms]

    return merged
