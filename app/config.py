"""Application configuration."""

import os

# Auto-detect GPU availability for EasyOCR (allow override via env)
try:
    import torch  # type: ignore
    force_cpu = os.getenv("FORCE_CPU", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    _USE_GPU = (not force_cpu) and bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
except Exception:
    _USE_GPU = False

# OCR settings
OCR_SETTINGS = {
    "languages": ["en"],
    "use_gpu": _USE_GPU,
}

# Device-specific presets for different serial label types
DEVICE_PRESETS = {
    "etched": {
        # For etched/engraved serials (low contrast, physical depth)
        "mode": "gray",
        "upscale_scale": 4.5,  # Increased for better detail
        "clip_limit": 3.0,  # Higher CLAHE for low contrast
        "bilateral_d": 9,
        "thresh_block_size": 45,  # Larger block for gradual changes
        "thresh_C": 9,
        "low_text": 0.15,  # Lower threshold for faint text
        "text_threshold": 0.35,
        "roi": True,
        "roi_top_k": 3,  # Increased to find more potential text regions
        "roi_pad": 12,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "division",  # Better for metallic surfaces
        "mag_ratio": 1.5,  # Higher magnification for EasyOCR
    },
    "sticker": {
        # For printed stickers (high contrast, flat surface)
        "mode": "binary",
        "upscale_scale": 3.5,  # Increased slightly
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.2,  # Slightly lower for better detection
        "text_threshold": 0.4,  # Slightly lower for better detection
        "roi": True,
        "roi_top_k": 2,
        "roi_pad": 8,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.0,  # Standard magnification
    },
    "screen": {
        # For serial on device screens (backlit, digital text)
        "mode": "gray",
        "upscale_scale": 2.5,  # Slightly increased
        "clip_limit": 1.5,
        "bilateral_d": 5,
        "thresh_block_size": 25,
        "thresh_C": 7,
        "low_text": 0.25,  # Slightly lower
        "text_threshold": 0.45,  # Slightly lower
        "roi": True,
        "roi_top_k": 2,
        "roi_pad": 5,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.0,  # Standard magnification
    },
    "default": {
        # Balanced settings for unknown label types
        "mode": "gray",
        "upscale_scale": 4.0,
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.18,  # Optimized based on testing
        "text_threshold": 0.38,  # Optimized based on testing
        "roi": True,
        "roi_top_k": 3,
        "roi_pad": 10,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.2,  # Slightly higher magnification
    }
}