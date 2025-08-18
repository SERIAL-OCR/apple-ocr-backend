"""Application configuration."""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# OCR Settings
OCR_SETTINGS = {
    "use_gpu": True,
    "languages": ["en"],
    "gpu_memory_fraction": 0.8,
    "batch_size": 4
}

# Device Presets
DEVICE_PRESETS = {
    "macbook": {
        "name": "MacBook (Etched)",
        "description": "MacBook with etched serial number",
        "preset": "etched",
        "roi_aspect_ratio": 4.0,
        "confidence_threshold": 0.75,
        "processing_params": {
            "upscale_scale": 2.5,
            "glare_reduction": "adaptive",
            "roi_top_k": 3,
            "adaptive_pad": True
        }
    },
    "iphone": {
        "name": "iPhone (Screen)",
        "description": "iPhone with on-screen serial number",
        "preset": "screen",
        "roi_aspect_ratio": 3.5,
        "confidence_threshold": 0.70,
        "processing_params": {
            "upscale_scale": 3.0,
            "glare_reduction": "multi",
            "roi_top_k": 2,
            "adaptive_pad": True
        }
    },
    "ipad": {
        "name": "iPad (Screen)",
        "description": "iPad with on-screen serial number",
        "preset": "screen",
        "roi_aspect_ratio": 3.0,
        "confidence_threshold": 0.70,
        "processing_params": {
            "upscale_scale": 3.0,
            "glare_reduction": "multi",
            "roi_top_k": 2,
            "adaptive_pad": True
        }
    },
    "imac": {
        "name": "iMac (Etched)",
        "description": "iMac with etched serial number",
        "preset": "etched",
        "roi_aspect_ratio": 4.5,
        "confidence_threshold": 0.75,
        "processing_params": {
            "upscale_scale": 2.5,
            "glare_reduction": "adaptive",
            "roi_top_k": 3,
            "adaptive_pad": True
        }
    },
    "macmini": {
        "name": "Mac Mini (Etched)",
        "description": "Mac Mini with etched serial number",
        "preset": "etched",
        "roi_aspect_ratio": 3.5,
        "confidence_threshold": 0.75,
        "processing_params": {
            "upscale_scale": 2.5,
            "glare_reduction": "adaptive",
            "roi_top_k": 3,
            "adaptive_pad": True
        }
    }
}

def get_device_preset(device_type: str) -> str:
    """Get the preset for a given device type."""
    device_type_lower = device_type.lower()
    
    # Check for exact matches first
    if device_type_lower in DEVICE_PRESETS:
        return DEVICE_PRESETS[device_type_lower]["preset"]
    
    # Check for partial matches
    for key, device_info in DEVICE_PRESETS.items():
        if key in device_type_lower or device_type_lower in key:
            return device_info["preset"]
    
    # Default to etched for Mac devices, screen for iOS devices
    if any(mac_key in device_type_lower for mac_key in ["mac", "imac", "macmini"]):
        return "etched"
    elif any(ios_key in device_type_lower for ios_key in ["iphone", "ipad"]):
        return "screen"
    else:
        return "etched"  # Default fallback

# Production Configuration (Simple dict-based approach)
PRODUCTION_CONFIG = {
    # Production Mode Configuration
    "PRODUCTION_MODE": os.getenv("PRODUCTION_MODE", "false").lower() == "true",
    "ENABLE_TESSERACT_FALLBACK": os.getenv("ENABLE_TESSERACT_FALLBACK", "true").lower() == "true",
    "MAX_PROCESSING_TIME": float(os.getenv("MAX_PROCESSING_TIME", "35.0")),
    "FALLBACK_STRATEGY": os.getenv("FALLBACK_STRATEGY", "hybrid"),
    
    # Performance Tuning
    "EARLY_STOP_CONFIDENCE": float(os.getenv("EARLY_STOP_CONFIDENCE", "0.65")),
    "USE_YOLO_ROI": os.getenv("USE_YOLO_ROI", "true").lower() == "true",
    "TRY_INVERT": os.getenv("TRY_INVERT", "true").lower() == "true",
    "TRY_MULTI_SCALE": os.getenv("TRY_MULTI_SCALE", "false").lower() == "true",
    
    # GPU Configuration
    "USE_GPU": os.getenv("USE_GPU", "true").lower() == "true",
    "PYTORCH_MPS_HIGH_WATERMARK_RATIO": float(os.getenv("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")),
    "OCR_BATCH_SIZE": int(os.getenv("OCR_BATCH_SIZE", "4")),
    
    # YOLO Configuration
    "YOLO_CONFIDENCE_THRESHOLD": float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5")),
    
    # Server Configuration
    "HOST": os.getenv("HOST", "0.0.0.0"),
    "PORT": int(os.getenv("PORT", "8000")),
    "RELOAD": os.getenv("RELOAD", "false").lower() == "true"
}

# Helper function to get config values
def get_config(key: str, default=None):
    """Get configuration value with fallback to default."""
    return PRODUCTION_CONFIG.get(key, default)

# Settings object for backward compatibility
class Settings:
    def __init__(self):
        for key, value in PRODUCTION_CONFIG.items():
            setattr(self, key, value)

settings = Settings()