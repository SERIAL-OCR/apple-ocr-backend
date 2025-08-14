"""
Quick test script for the improved OCR pipeline.

This script provides a simple way to test the OCR improvements without requiring
any of the more complex dependencies like YOLO or Tesseract.

Usage:
    python scripts/quick_test.py --image "Apple serial/IMG-20250813-WA0024.jpg" --preset etched-dark
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.ocr_adapter_improved import progressive_process
from app.config import DEVICE_PRESETS


def main():
    parser = argparse.ArgumentParser(description="Quick test for improved OCR pipeline")
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument("--preset", default="etched-dark", help="Device preset to use")
    
    args = parser.parse_args()
    
    # Check if image exists
    if not os.path.exists(args.image):
        print(f"Error: Image file not found: {args.image}")
        return
    
    # Load image
    print(f"Processing image: {args.image}")
    with open(args.image, "rb") as f:
        image_bytes = f.read()
    
    # Get preset parameters
    extract_params = {}
    if args.preset in DEVICE_PRESETS:
        extract_params = DEVICE_PRESETS[args.preset].copy()
        print(f"Using preset: {args.preset}")
    else:
        print(f"Warning: Unknown preset '{args.preset}', using default parameters")
    
    # Create debug directory
    debug_dir = "exports/debug"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Create debug path
    filename = os.path.basename(args.image)
    debug_path = os.path.join(debug_dir, f"{os.path.splitext(filename)[0]}_debug")
    
    # Start timer
    start_time = time.time()
    
    # Process image with progressive pipeline
    # Disable YOLO and Tesseract to avoid dependency issues
    
    # Filter out parameters that aren't accepted by progressive_process
    # Only keep parameters that are valid for the function
    valid_params = {
        'min_confidence': extract_params.get('min_confidence', 0.0),
        'early_stop_confidence': extract_params.get('early_stop_confidence', 0.95),
        'max_processing_time': extract_params.get('max_processing_time', 30.0)
    }
    
    results = progressive_process(
        image_bytes=image_bytes,
        debug_save_path=debug_path,
        use_tesseract_fallback=False,
        use_yolo_roi=False,
        **valid_params
    )
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Print results
    print(f"\nProcessing time: {processing_time:.2f} seconds")
    if results:
        print("\nResults:")
        for i, (serial, confidence) in enumerate(results):
            print(f"  {i+1}. {serial} (confidence: {confidence:.3f})")
        
        print(f"\nTop result: {results[0][0]} with confidence {results[0][1]:.3f}")
    else:
        print("No results found")
    
    print(f"\nDebug images saved to: {debug_path}*.png")


if __name__ == "__main__":
    main()
