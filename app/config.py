"""Application configuration."""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# On-device OCR Configuration
CONFIG = {
    # API Security
    "VALID_API_KEYS": os.getenv("VALID_API_KEYS", "phase2-pilot-key-2024"),
    
    # Validation Thresholds
    "MIN_ACCEPTANCE_CONFIDENCE": float(os.getenv("MIN_ACCEPTANCE_CONFIDENCE", "0.65")),
    "MIN_SUBMISSION_CONFIDENCE": float(os.getenv("MIN_SUBMISSION_CONFIDENCE", "0.3")),
    
    # Observability
    "ENABLE_DETAILED_LOGGING": os.getenv("ENABLE_DETAILED_LOGGING", "true").lower() == "true",
    "LOG_SERIAL_MASKING": os.getenv("LOG_SERIAL_MASKING", "true").lower() == "true",
    
    # Performance
    "MAX_SUBMISSIONS_PER_MINUTE": int(os.getenv("MAX_SUBMISSIONS_PER_MINUTE", "60")),
    "ENABLE_RATE_LIMITING": os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true",
    
    # Production Mode
    "PRODUCTION_MODE": os.getenv("PRODUCTION_MODE", "false").lower() == "true"
}

def get_config(key: str, default=None):
    """Get configuration value with fallback to environment variables."""
    # Check Phase 2.1 config first
    if key in CONFIG:
        return CONFIG[key]
    
    # Check environment variables
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    
    # Return default
    return default


def get_phase2_config() -> dict:
    """Get Phase 2.1 configuration for client consumption."""
    return {
        "min_acceptance_confidence": CONFIG["MIN_ACCEPTANCE_CONFIDENCE"],
        "min_submission_confidence": CONFIG["MIN_SUBMISSION_CONFIDENCE"],
        "production_mode": CONFIG["PRODUCTION_MODE"],
        "rate_limiting_enabled": CONFIG["ENABLE_RATE_LIMITING"],
        "max_submissions_per_minute": CONFIG["MAX_SUBMISSIONS_PER_MINUTE"]
    }