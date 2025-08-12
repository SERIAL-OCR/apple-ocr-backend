"""Application configuration."""

# Auto-detect GPU availability for EasyOCR
try:
    import torch  # type: ignore
    _USE_GPU = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
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
        "upscale_scale": 4.0,
        "clip_limit": 3.0,  # Higher CLAHE for low contrast
        "bilateral_d": 9,
        "thresh_block_size": 45,  # Larger block for gradual changes
        "thresh_C": 9,
        "low_text": 0.15,  # Lower threshold for faint text
        "text_threshold": 0.35,
        "roi": True,
        "roi_pad": 12,
        "glare_reduction": "division",  # Better for metallic surfaces
    },
    "sticker": {
        # For printed stickers (high contrast, flat surface)
        "mode": "binary",
        "upscale_scale": 3.0,
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.25,
        "text_threshold": 0.45,
        "roi": True,
        "roi_pad": 8,
        "glare_reduction": "tophat",  # Better for glossy stickers
    },
    "screen": {
        # For serial on device screens (backlit, digital text)
        "mode": "gray",
        "upscale_scale": 2.0,  # Less upscaling needed for digital
        "clip_limit": 1.5,
        "bilateral_d": 5,
        "thresh_block_size": 25,
        "thresh_C": 7,
        "low_text": 0.3,
        "text_threshold": 0.5,
        "roi": True,
        "roi_pad": 5,
        "glare_reduction": None,  # Usually not needed for screens
    },
    "default": {
        # Balanced settings for unknown label types
        "mode": "gray",
        "upscale_scale": 4.0,
        "clip_limit": 2.0,
        "bilateral_d": 7,
        "thresh_block_size": 35,
        "thresh_C": 11,
        "low_text": 0.2,
        "text_threshold": 0.4,
        "roi": True,
        "roi_pad": 10,
        "glare_reduction": None,
    }
}