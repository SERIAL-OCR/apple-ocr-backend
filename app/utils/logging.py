"""
Structured logging utilities for the OCR application.

This module provides structured logging functions for:
- OCR processing timings
- Detection misses and failures
- Debug asset paths
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create logger
logger = logging.getLogger("apple-ocr")

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure file handler for structured logs
STRUCTURED_LOG_FILE = LOGS_DIR / "ocr_structured.jsonl"
file_handler = logging.FileHandler(STRUCTURED_LOG_FILE)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)


class Timer:
    """Simple context manager for timing code blocks."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time


def log_structured(
    event_type: str,
    message: str,
    data: Dict[str, Any],
    level: int = logging.INFO,
) -> None:
    """
    Log a structured event with additional data.
    
    Args:
        event_type: Type of event (e.g., 'ocr_process', 'detection_miss')
        message: Human-readable message
        data: Additional structured data
        level: Logging level
    """
    structured_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "message": message,
        **data
    }
    
    # Log as JSON to file
    logger.log(level, json.dumps(structured_data))
    
    # Also log human-readable message to console
    logger.log(level, f"{event_type}: {message}")


def log_ocr_timing(
    image_id: str,
    total_time: float,
    preprocessing_time: float,
    detection_time: float,
    validation_time: float,
    serials_found: int,
    top_confidence: Optional[float] = None,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log OCR processing timing information.
    
    Args:
        image_id: Identifier for the processed image
        total_time: Total processing time in seconds
        preprocessing_time: Time spent on preprocessing in seconds
        detection_time: Time spent on text detection in seconds
        validation_time: Time spent on validation in seconds
        serials_found: Number of serials found
        top_confidence: Confidence of the top result (if any)
        additional_data: Any additional data to include
    """
    data = {
        "image_id": image_id,
        "timing": {
            "total_ms": round(total_time * 1000, 2),
            "preprocessing_ms": round(preprocessing_time * 1000, 2),
            "detection_ms": round(detection_time * 1000, 2),
            "validation_ms": round(validation_time * 1000, 2),
        },
        "results": {
            "serials_found": serials_found,
            "top_confidence": top_confidence,
        }
    }
    
    if additional_data:
        data.update(additional_data)
    
    log_structured(
        event_type="ocr_timing",
        message=f"OCR processed {image_id} in {total_time:.2f}s, found {serials_found} serials",
        data=data,
    )


def log_detection_miss(
    image_id: str,
    params: Dict[str, Any],
    debug_path: Optional[str] = None,
    expected_serial: Optional[str] = None,
) -> None:
    """
    Log information about a detection miss.
    
    Args:
        image_id: Identifier for the processed image
        params: OCR parameters used
        debug_path: Path to debug image (if saved)
        expected_serial: Expected serial (if known)
    """
    data = {
        "image_id": image_id,
        "params": params,
    }
    
    if debug_path:
        data["debug_path"] = debug_path
    
    if expected_serial:
        data["expected_serial"] = expected_serial
    
    log_structured(
        event_type="detection_miss",
        message=f"Failed to detect serial in {image_id}",
        data=data,
        level=logging.WARNING,
    )


def log_debug_asset(
    image_id: str,
    asset_type: str,
    asset_path: str,
    related_serial: Optional[str] = None,
    confidence: Optional[float] = None,
) -> None:
    """
    Log information about a saved debug asset.
    
    Args:
        image_id: Identifier for the processed image
        asset_type: Type of asset (e.g., 'preprocessed', 'roi', 'failed')
        asset_path: Path to the saved asset
        related_serial: Related serial number (if any)
        confidence: Confidence score (if applicable)
    """
    data = {
        "image_id": image_id,
        "asset_type": asset_type,
        "asset_path": asset_path,
    }
    
    if related_serial:
        data["related_serial"] = related_serial
    
    if confidence is not None:
        data["confidence"] = confidence
    
    log_structured(
        event_type="debug_asset",
        message=f"Saved {asset_type} debug asset for {image_id}",
        data=data,
    )


def log_api_request(
    endpoint: str,
    method: str,
    params: Dict[str, Any],
    status_code: int,
    response_time: float,
    client_ip: Optional[str] = None,
) -> None:
    """
    Log information about an API request.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        params: Request parameters
        status_code: HTTP status code
        response_time: Response time in seconds
        client_ip: Client IP address (if available)
    """
    data = {
        "endpoint": endpoint,
        "method": method,
        "params": params,
        "status_code": status_code,
        "response_time_ms": round(response_time * 1000, 2),
    }
    
    if client_ip:
        data["client_ip"] = client_ip
    
    log_structured(
        event_type="api_request",
        message=f"{method} {endpoint} - {status_code} in {response_time:.2f}s",
        data=data,
    )
