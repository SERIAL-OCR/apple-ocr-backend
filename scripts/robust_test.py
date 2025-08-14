"""
Robust test script for the OCR pipeline with error handling.

This script provides a robust way to test the OCR improvements with
better error handling for common issues.

Usage:
    python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0024.jpg" --preset etched-dark
"""

import os
import sys
import argparse
import time
import cv2
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.ocr_adapter_improved import extract_serials
from app.config import DEVICE_PRESETS


def process_image_safely(image_path, preset=None, debug_save_path=None):
    """Process an image with robust error handling."""
    print(f"Processing image: {image_path}")
    
    try:
        # Load image directly with OpenCV instead of using bytes
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image {image_path}")
            return None
        
        # Get preset parameters
        extract_params = {}
        if preset and preset in DEVICE_PRESETS:
            extract_params = DEVICE_PRESETS[preset].copy()
            print(f"Using preset: {preset}")
        else:
            print(f"Using default parameters")
        
        # Convert image to bytes for the OCR function
        _, img_bytes = cv2.imencode(".png", img)
        image_bytes = img_bytes.tobytes()
        
        # Start timer
        start_time = time.time()
        
        # Process with basic parameters, avoiding problematic ones
        safe_params = {
            'min_confidence': extract_params.get('min_confidence', 0.0),
            'early_stop_confidence': extract_params.get('early_stop_confidence', 0.95),
            'smart_rotation': True,
            'fine_rotation': False
        }
        
        # Add safe preprocessing parameters
        if 'upscale_scale' in extract_params:
            safe_params['upscale_scale'] = extract_params['upscale_scale']
        
        if 'glare_reduction' in extract_params:
            safe_params['glare_reduction'] = extract_params['glare_reduction']
            
        # Use grayscale mode which is safer
        safe_params['mode'] = 'gray'
        
        # Disable features that might cause issues
        safe_params['roi'] = False
        
        # Process image
        results = extract_serials(
            image_bytes=image_bytes,
            debug_save_path=debug_save_path,
            **safe_params
        )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return {
            'results': results,
            'processing_time': processing_time
        }
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        
        # Try with even more basic parameters as fallback
        try:
            print("Trying fallback with minimal parameters...")
            
            # Convert image to bytes
            _, img_bytes = cv2.imencode(".png", img)
            image_bytes = img_bytes.tobytes()
            
            # Start timer
            start_time = time.time()
            
            # Process with minimal parameters
            results = extract_serials(
                image_bytes=image_bytes,
                debug_save_path=debug_save_path,
                min_confidence=0.0,
                mode="gray",
                upscale_scale=3.0,
                roi=False,
                fine_rotation=False
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            return {
                'results': results,
                'processing_time': processing_time,
                'fallback': True
            }
            
        except Exception as e2:
            print(f"Fallback also failed: {str(e2)}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Robust test for OCR pipeline")
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument("--preset", default="etched-dark", help="Device preset to use")
    parser.add_argument("--no-debug", action="store_true", help="Disable saving debug images")
    
    args = parser.parse_args()
    
    # Check if image exists
    if not os.path.exists(args.image):
        print(f"Error: Image file not found: {args.image}")
        return
    
    # Create debug directory
    debug_dir = "exports/debug"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Create debug path
    filename = os.path.basename(args.image)
    debug_path = None
    if not args.no_debug:
        debug_path = os.path.join(debug_dir, f"{os.path.splitext(filename)[0]}_robust_debug")
    
    # Process image
    result = process_image_safely(
        image_path=args.image,
        preset=args.preset,
        debug_save_path=debug_path
    )
    
    # Print results
    if result:
        print(f"\nProcessing time: {result['processing_time']:.2f} seconds")
        
        if 'fallback' in result and result['fallback']:
            print("Note: Used fallback processing with minimal parameters")
        
        if result['results']:
            print("\nResults:")
            for i, (serial, confidence) in enumerate(result['results']):
                print(f"  {i+1}. {serial} (confidence: {confidence:.3f})")
            
            print(f"\nTop result: {result['results'][0][0]} with confidence {result['results'][0][1]:.3f}")
        else:
            print("No results found")
        
        if debug_path:
            print(f"\nDebug images saved to: {debug_path}*.png")
    else:
        print("Processing failed completely")


if __name__ == "__main__":
    main()

