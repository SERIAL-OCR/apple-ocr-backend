#!/usr/bin/env python3
"""
Test script for the progressive processing pipeline with Apple Silicon support.
"""

import argparse
import cv2
import time
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.pipeline.ocr_adapter_improved import progressive_process


def main():
    parser = argparse.ArgumentParser(description="Test progressive OCR processing")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--preset", default="apple_silicon", help="Preset to use (default: apple_silicon)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Maximum processing time in seconds")
    parser.add_argument("--debug", action="store_true", help="Save debug images")
    args = parser.parse_args()
    
    # Load image
    print(f"\nProcessing image: {args.image}")
    print(f"Using preset: {args.preset}")
    print(f"Timeout: {args.timeout} seconds")
    
    # Read image
    img = cv2.imread(args.image)
    if img is None:
        print(f"Error: Could not read image {args.image}")
        return 1
    
    # Convert to bytes
    _, img_bytes = cv2.imencode('.jpg', img)
    img_bytes = img_bytes.tobytes()
    
    # Create debug path if needed
    debug_path = None
    if args.debug:
        os.makedirs("exports/debug", exist_ok=True)
        debug_path = f"exports/debug/{Path(args.image).stem}_progressive_debug.png"
    
    # Process image
    start_time = time.time()
    
    # Extract parameters from preset if specified
    extract_params = {}
    if args.preset:
        from app.config import OCR_PRESETS
        preset_config = OCR_PRESETS.get(args.preset, {})
        if preset_config:
            extract_params = preset_config
    
    results = progressive_process(
        img_bytes,
        min_confidence=0.0,
        early_stop_confidence=0.9,
        debug_save_path=debug_path,
        max_processing_time=args.timeout,
        debug_steps=args.debug,
        **extract_params
    )
    
    processing_time = time.time() - start_time
    
    print(f"\nProcessing time: {processing_time:.2f} seconds")
    
    if not results:
        print("No results found")
    else:
        print("\nResults:")
        for i, (serial, confidence) in enumerate(results[:8], 1):  # Show top 8 results
            print(f"  {i}. {serial} (confidence: {confidence:.3f})")
        
        print(f"\nTop result: {results[0][0]} with confidence {results[0][1]:.3f}")
    
    if debug_path:
        print(f"\nDebug images saved to: {debug_path}*")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
