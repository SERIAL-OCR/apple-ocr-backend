#!/usr/bin/env python3
"""
Test the Tesseract OCR fallback mechanism.

This script allows testing the Tesseract OCR fallback on a single image or a directory.

Usage:
    python test_tesseract_fallback.py --image "Apple serial/IMG-20250813-WA0024.jpg"
    python test_tesseract_fallback.py --dir "Apple serial" --limit 5
"""

import os
import sys
import argparse
import cv2
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.tesseract_adapter import extract_serials_with_tesseract, TESSERACT_AVAILABLE


def process_image_with_tesseract(
    image_path: str,
    save_debug: bool = True,
) -> Dict:
    """
    Process a single image with Tesseract OCR.
    
    Args:
        image_path: Path to the image
        save_debug: Whether to save debug images
        
    Returns:
        Dictionary with results
    """
    print(f"\nProcessing {image_path} with Tesseract OCR")
    
    if not TESSERACT_AVAILABLE:
        print("Tesseract is not available. Please install Tesseract OCR.")
        return {"image_path": image_path, "results": [], "error": "Tesseract not available"}
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return {"image_path": image_path, "results": [], "error": "Could not read image"}
    
    # Create debug directory
    if save_debug:
        debug_dir = "exports/debug_tesseract"
        os.makedirs(debug_dir, exist_ok=True)
    
    # Start timer
    start_time = time.time()
    
    # Process with Tesseract
    results = extract_serials_with_tesseract(img)
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Print results
    print(f"Processing time: {processing_time:.2f} seconds")
    if results:
        print("Results:")
        for serial, confidence in results[:3]:  # Show top 3 results
            print(f"  {serial} (confidence: {confidence:.3f})")
    else:
        print("No results found")
    
    # Save debug image if requested
    if save_debug and results:
        filename = os.path.basename(image_path)
        debug_path = os.path.join(debug_dir, f"{os.path.splitext(filename)[0]}_tesseract.jpg")
        
        # Draw results on image
        img_copy = img.copy()
        cv2.putText(
            img_copy,
            f"{results[0][0]} ({results[0][1]:.3f})",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.imwrite(debug_path, img_copy)
    
    return {
        "image_path": image_path,
        "results": results,
        "processing_time": processing_time,
    }


def process_directory_with_tesseract(
    dir_path: str,
    save_debug: bool = True,
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Process all images in a directory with Tesseract OCR.
    
    Args:
        dir_path: Path to the directory
        save_debug: Whether to save debug images
        limit: Maximum number of images to process
        
    Returns:
        List of result dictionaries
    """
    print(f"Processing directory: {dir_path} with Tesseract OCR")
    
    # Find image files
    image_files = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                image_files.append(os.path.join(root, file))
    
    # Sort image files
    image_files.sort()
    
    # Limit number of images if specified
    if limit is not None and limit > 0:
        image_files = image_files[:limit]
    
    print(f"Found {len(image_files)} images to process")
    
    # Process images
    results = []
    for i, image_path in enumerate(image_files):
        print(f"\nImage {i+1}/{len(image_files)}")
        result = process_image_with_tesseract(
            image_path=image_path,
            save_debug=save_debug,
        )
        results.append(result)
    
    # Calculate statistics
    total_time = sum(r["processing_time"] for r in results)
    avg_time = total_time / len(results) if results else 0
    
    # Count results with at least one detection
    detected = sum(1 for r in results if r["results"])
    detection_rate = detected / len(results) * 100 if results else 0
    
    print(f"\nProcessed {len(results)} images with Tesseract OCR")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Average processing time: {avg_time:.2f} seconds per image")
    print(f"Detection rate: {detection_rate:.1f}% ({detected}/{len(results)})")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Test Tesseract OCR fallback")
    parser.add_argument("--image", help="Path to a single image")
    parser.add_argument("--dir", help="Path to a directory of images")
    parser.add_argument("--no-debug", action="store_true", help="Disable saving debug images")
    parser.add_argument("--limit", type=int, help="Limit number of images to process")
    
    args = parser.parse_args()
    
    if not args.image and not args.dir:
        parser.error("Either --image or --dir must be specified")
    
    if not TESSERACT_AVAILABLE:
        print("Warning: Tesseract is not available. Please install Tesseract OCR.")
        print("You can download it from: https://github.com/tesseract-ocr/tesseract")
        print("After installation, set the TESSERACT_CMD environment variable to the path of the tesseract executable.")
        sys.exit(1)
    
    if args.image:
        process_image_with_tesseract(
            image_path=args.image,
            save_debug=not args.no_debug,
        )
    else:
        process_directory_with_tesseract(
            dir_path=args.dir,
            save_debug=not args.no_debug,
            limit=args.limit,
        )


if __name__ == "__main__":
    main()
