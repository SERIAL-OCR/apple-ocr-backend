"""
Test the OCR pipeline with various optimizations.

This script allows testing the OCR pipeline on a single image or a directory
without requiring YOLO training.

Usage:
    python test_ocr_pipeline.py --image "Apple serial/IMG-20250813-WA0024.jpg" --preset etched
    python test_ocr_pipeline.py --dir "Apple serial" --preset etched-dark
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

from app.pipeline.ocr_adapter_improved import progressive_process
from app.config import DEVICE_PRESETS


def process_image(
    image_path: str,
    preset: Optional[str] = None,
    use_progressive: bool = True,
    use_tesseract: bool = True,
    use_yolo: bool = False,
    save_debug: bool = True,
) -> Dict:
    """
    Process a single image with the OCR pipeline.
    
    Args:
        image_path: Path to the image
        preset: Device preset to use
        use_progressive: Whether to use progressive processing
        use_tesseract: Whether to use Tesseract fallback
        use_yolo: Whether to use YOLO ROI detection
        save_debug: Whether to save debug images
        
    Returns:
        Dictionary with results
    """
    print(f"\nProcessing {image_path}")
    
    # Load image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Get preset parameters
    extract_params = {}
    if preset and preset in DEVICE_PRESETS:
        extract_params = DEVICE_PRESETS[preset].copy()
        print(f"Using preset: {preset}")
    
    # Create debug directory
    debug_dir = "exports/debug"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Create debug path
    filename = os.path.basename(image_path)
    debug_path = os.path.join(debug_dir, f"{os.path.splitext(filename)[0]}_debug") if save_debug else None
    
    # Start timer
    start_time = time.time()
    
    # Process image
    if use_progressive:
        # Filter out parameters that aren't accepted by progressive_process
        valid_params = {
            'min_confidence': extract_params.get('min_confidence', 0.0),
            'early_stop_confidence': extract_params.get('early_stop_confidence', 0.95),
            'max_processing_time': extract_params.get('max_processing_time', 30.0)
        }
        
        results = progressive_process(
            image_bytes=image_bytes,
            debug_save_path=debug_path,
            use_tesseract_fallback=use_tesseract,
            use_yolo_roi=use_yolo,
            **valid_params
        )
    else:
        # Import here to avoid circular imports
        from app.pipeline.ocr_adapter_improved import extract_serials
        results = extract_serials(
            image_bytes=image_bytes,
            debug_save_path=debug_path,
            **extract_params
        )
    
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
    
    return {
        "image_path": image_path,
        "results": results,
        "processing_time": processing_time,
        "preset": preset,
    }


def process_directory(
    dir_path: str,
    preset: Optional[str] = None,
    use_progressive: bool = True,
    use_tesseract: bool = True,
    use_yolo: bool = False,
    save_debug: bool = True,
    limit: Optional[int] = None,
) -> List[Dict]:
    """
    Process all images in a directory.
    
    Args:
        dir_path: Path to the directory
        preset: Device preset to use
        use_progressive: Whether to use progressive processing
        use_tesseract: Whether to use Tesseract fallback
        use_yolo: Whether to use YOLO ROI detection
        save_debug: Whether to save debug images
        limit: Maximum number of images to process
        
    Returns:
        List of result dictionaries
    """
    print(f"Processing directory: {dir_path}")
    
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
        result = process_image(
            image_path=image_path,
            preset=preset,
            use_progressive=use_progressive,
            use_tesseract=use_tesseract,
            use_yolo=use_yolo,
            save_debug=save_debug,
        )
        results.append(result)
    
    # Calculate statistics
    total_time = sum(r["processing_time"] for r in results)
    avg_time = total_time / len(results) if results else 0
    
    # Count results with at least one detection
    detected = sum(1 for r in results if r["results"])
    detection_rate = detected / len(results) * 100 if results else 0
    
    print(f"\nProcessed {len(results)} images")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Average processing time: {avg_time:.2f} seconds per image")
    print(f"Detection rate: {detection_rate:.1f}% ({detected}/{len(results)})")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Test the OCR pipeline")
    parser.add_argument("--image", help="Path to a single image")
    parser.add_argument("--dir", help="Path to a directory of images")
    parser.add_argument("--preset", help="Device preset to use")
    parser.add_argument("--no-progressive", action="store_true", help="Disable progressive processing")
    parser.add_argument("--no-tesseract", action="store_true", help="Disable Tesseract fallback")
    parser.add_argument("--use-yolo", action="store_true", help="Enable YOLO ROI detection")
    parser.add_argument("--no-debug", action="store_true", help="Disable saving debug images")
    parser.add_argument("--limit", type=int, help="Limit number of images to process")
    
    args = parser.parse_args()
    
    if not args.image and not args.dir:
        parser.error("Either --image or --dir must be specified")
    
    if args.image:
        process_image(
            image_path=args.image,
            preset=args.preset,
            use_progressive=not args.no_progressive,
            use_tesseract=not args.no_tesseract,
            use_yolo=args.use_yolo,
            save_debug=not args.no_debug,
        )
    else:
        process_directory(
            dir_path=args.dir,
            preset=args.preset,
            use_progressive=not args.no_progressive,
            use_tesseract=not args.no_tesseract,
            use_yolo=args.use_yolo,
            save_debug=not args.no_debug,
            limit=args.limit,
        )


if __name__ == "__main__":
    main()
