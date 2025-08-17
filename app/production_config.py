"""
Production Configuration for Apple OCR Backend
This file contains production-ready settings for deployment
"""

# Production Mode Configuration
PRODUCTION_MODE = True
ENABLE_TESSERACT_FALLBACK = True
MAX_PROCESSING_TIME = 35.0
FALLBACK_STRATEGY = "hybrid"

# Performance Tuning
EARLY_STOP_CONFIDENCE = 0.75
USE_YOLO_ROI = True
TRY_INVERT = True
TRY_MULTI_SCALE = False

# GPU Configuration
USE_GPU = True
PYTORCH_MPS_HIGH_WATERMARK_RATIO = 0.0
OCR_BATCH_SIZE = 4

# YOLO Configuration
YOLO_CONFIDENCE_THRESHOLD = 0.5

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
RELOAD = False

# Fallback Strategy Options
FALLBACK_STRATEGIES = {
    "easyocr_only": "Fast processing with EasyOCR only (development)",
    "tesseract_only": "Reliable processing with Tesseract only (legacy)",
    "hybrid": "Balanced approach with EasyOCR + Tesseract fallback (production)"
}

# Production Performance Targets
PERFORMANCE_TARGETS = {
    "fast_success_rate": 0.85,  # 85% of images should succeed in fast stages
    "max_processing_time": 35.0,  # Maximum processing time in seconds
    "fallback_activation_rate": 0.15,  # Only 15% should need fallback
    "overall_success_rate": 0.98  # 98% overall success rate
}

# Fallback Configuration
FALLBACK_CONFIG = {
    "enhanced_easyocr_attempts": 3,  # Number of enhanced EasyOCR attempts
    "tesseract_timeout": 15.0,  # Tesseract processing timeout
    "confidence_boost": 0.05,  # Confidence boost for fallback results
    "min_fallback_confidence": 0.6  # Minimum confidence for fallback results
}
