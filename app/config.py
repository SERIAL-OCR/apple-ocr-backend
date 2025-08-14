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
        "low_text": 0.12,  # Lower threshold for faint text
        "text_threshold": 0.30,
        "roi": True,
        "roi_top_k": 3,  # Increased to find more potential text regions
        "roi_pad": 12,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "division",  # Better for metallic surfaces
        "mag_ratio": 1.8,  # Higher magnification for EasyOCR
    },
    "etched-dark": {
        # For etched serials on dark metallic surfaces
        "mode": "gray",
        "upscale_scale": 5.0,  # Higher upscaling for dark surfaces
        "clip_limit": 3.5,  # Higher contrast enhancement
        "bilateral_d": 9,
        "thresh_block_size": 45,
        "thresh_C": 7,  # Lower threshold for better extraction
        "low_text": 0.10,  # Very permissive text detection
        "text_threshold": 0.25,  # Very permissive text threshold
        "roi": True,
        "roi_top_k": 3,
        "roi_pad": 15,  # Larger padding
        "adaptive_pad": True,
        "glare_reduction": "multi",  # Multi-scale glare handling
        "mag_ratio": 2.0,  # Maximum magnification
    },
    "etched-light": {
        # For etched serials on light/reflective surfaces
        "mode": "binary",  # Binary mode works better for high contrast
        "upscale_scale": 4.0,
        "clip_limit": 2.5,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 12,  # Higher threshold for better separation
        "low_text": 0.15,
        "text_threshold": 0.35,
        "roi": True,
        "roi_top_k": 3,
        "roi_pad": 10,
        "adaptive_pad": True,
        "glare_reduction": "multi",  # Multi-scale glare handling
        "mag_ratio": 1.5,
    },
    "sticker": {
        # For printed stickers (high contrast, flat surface)
        "mode": "binary",
        "upscale_scale": 3.5,  # Increased slightly
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.15,  # Reduced for better detection
        "text_threshold": 0.35,  # Reduced for better detection
        "roi": True,
        "roi_top_k": 2,
        "roi_pad": 8,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.2,  # Increased magnification
    },
    "sticker-damaged": {
        # For damaged/worn stickers
        "mode": "binary",
        "upscale_scale": 4.0,  # Higher upscaling for worn text
        "clip_limit": 2.5,  # Higher contrast enhancement
        "bilateral_d": 9,  # More aggressive smoothing
        "thresh_block_size": 45,
        "thresh_C": 9,
        "low_text": 0.12,  # More permissive
        "text_threshold": 0.30,  # More permissive
        "roi": True,
        "roi_top_k": 3,  # Try more regions
        "roi_pad": 12,
        "adaptive_pad": True,
        "glare_reduction": "adaptive",
        "mag_ratio": 1.5,  # Higher magnification
    },
    "screen": {
        # For serial on device screens (backlit, digital text)
        "mode": "gray",
        "upscale_scale": 2.5,  # Slightly increased
        "clip_limit": 1.5,
        "bilateral_d": 5,
        "thresh_block_size": 25,
        "thresh_C": 7,
        "low_text": 0.20,  # Further reduced
        "text_threshold": 0.40,  # Further reduced
        "roi": True,
        "roi_top_k": 2,
        "roi_pad": 5,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.2,  # Increased magnification
    },
    "screen-glare": {
        # For screens with significant glare/reflection
        "mode": "gray",
        "upscale_scale": 3.0,
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 9,
        "low_text": 0.15,
        "text_threshold": 0.35,
        "roi": True,
        "roi_top_k": 3,
        "roi_pad": 8,
        "adaptive_pad": True,
        "glare_reduction": "multi",  # Multi-scale glare handling
        "mag_ratio": 1.5,
    },
    "default": {
        # Balanced settings for unknown label types
        "mode": "gray",
        "upscale_scale": 4.0,
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.15,  # Further optimized based on testing
        "text_threshold": 0.35,  # Further optimized based on testing
        "roi": True,
        "roi_top_k": 3,
        "roi_pad": 10,
        "adaptive_pad": True,  # Use adaptive padding
        "glare_reduction": "adaptive",  # Auto-select best method
        "mag_ratio": 1.5,  # Increased magnification
    }
}