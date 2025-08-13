from __future__ import annotations

from typing import Optional, Tuple, List, Iterable, Set, Dict
import logging
import os

import cv2
import numpy as np
import easyocr

from app.utils.validation import is_valid_apple_serial
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
        except Exception:
            gpu_info = "torch_unavailable"
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
        
        logger.debug(f"Auto-selected glare reduction: {method} (mean={mean_val:.1f}, std={std_val:.1f})")
    
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
        gray = _reduce_glare(gray, method=glare_reduction)
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


def _expand_ambiguous(text: str) -> Set[str]:
    """Generate all possible variants by replacing ambiguous characters."""
    variants: Set[str] = {text}
    for idx, ch in enumerate(text):
        rep = _AMBIGUOUS_MAP.get(ch)
        if rep:
            for v in list(variants):
                variants.add(v[:idx] + rep + v[idx + 1:])
    return variants


def _normalize_ambiguous(text: str) -> str:
    """Normalize text by replacing ambiguous characters with their canonical form."""
    up = text.strip().upper()
    return "".join(_AMBIGUOUS_MAP.get(ch, ch) for ch in up)


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
    
    serials: List[Tuple[str, float]] = []
    for bbox, text, confidence in results:
        base = text.strip().upper().replace(" ", "")
        candidates = _expand_ambiguous(base)
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


def extract_serials(
    image_bytes: bytes,
    min_confidence: float = 0.0,
    debug_save_path: Optional[str] = None,
    try_rotations: Iterable[int] = (0, 90, 180, 270),
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
    for rgb, rgb_inv in zip(imgs_to_scan, inv_to_scan):
        for ang in try_rotations:
            rimg = _rotate_image(rgb, ang)
            all_serials.extend(
                _read_serials_from_image(
                    rimg, 
                    min_confidence=min_confidence, 
                    low_text=low_text, 
                    text_threshold=text_threshold,
                    mag_ratio=mag_ratio,
                )
            )
            rimg_inv = _rotate_image(rgb_inv, ang)
            all_serials.extend(
                _read_serials_from_image(
                    rimg_inv, 
                    min_confidence=min_confidence, 
                    low_text=low_text, 
                    text_threshold=text_threshold,
                    mag_ratio=mag_ratio,
                )
            )

    # Aggregate by normalized (ambiguous collapsed) key
    score_by_norm: Dict[str, float] = {}
    best_variant_by_norm: Dict[str, Tuple[str, float]] = {}
    for s, c in all_serials:
        norm = _normalize_ambiguous(s)
        score_by_norm[norm] = score_by_norm.get(norm, 0.0) + c
        if norm not in best_variant_by_norm or c > best_variant_by_norm[norm][1]:
            best_variant_by_norm[norm] = (s, c)

    # Return best variants ordered by aggregated score
    ordered_norms = sorted(score_by_norm.items(), key=lambda kv: kv[1], reverse=True)
    merged: List[Tuple[str, float]] = [(best_variant_by_norm[n][0], best_variant_by_norm[n][1]) for n, _ in ordered_norms]

    return merged
