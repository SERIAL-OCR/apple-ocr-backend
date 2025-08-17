#!/usr/bin/env python3
"""
Test the full OCR pipeline: preprocessing -> OCR -> post-processing
"""

import argparse
import cv2
import time
import os
import sys
from pathlib import Path
import numpy as np

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.pipeline.ocr_adapter_improved import (
    preprocess_image, 
    _read_serials_from_image,
    _normalize_ambiguous,
    _expand_ambiguous,
    _detect_text_orientation,
    _get_smart_rotation_angles
)
from app.pipeline.yolo_detector import detect_serial_regions
from app.utils.validation import is_valid_apple_serial


def test_preprocessing(image_path, preset="apple_silicon"):
    """Test image preprocessing step by step."""
    print(f"\n=== Testing Preprocessing ===")
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return None
    
    # Convert to bytes
    _, img_bytes = cv2.imencode('.jpg', img)
    img_bytes = img_bytes.tobytes()
    
    # Test different preprocessing modes
    modes = ["gray", "binary"]
    upscale_scales = [2.0, 3.0, 4.0]
    
    for mode in modes:
        for upscale in upscale_scales:
            print(f"\n--- Mode: {mode}, Upscale: {upscale}x ---")
            
            try:
                # Test preprocessing
                start_time = time.time()
                processed = preprocess_image(
                    img_bytes,
                    mode=mode,
                    upscale_scale=upscale,
                    clip_limit=2.0,
                    bilateral_d=7,
                    thresh_block_size=35,
                    thresh_C=11,
                    glare_reduction="adaptive",
                    sharpen=True,
                    debug_steps=True,
                    debug_save_path=f"exports/debug/test_{Path(image_path).stem}_{mode}_{upscale}x.png"
                )
                preprocessing_time = time.time() - start_time
                
                print(f"  Preprocessing time: {preprocessing_time:.2f}s")
                print(f"  Output shape: {processed.shape}")
                print(f"  Output dtype: {processed.dtype}")
                print(f"  Value range: {processed.min()} - {processed.max()}")
                
                # Save processed image
                os.makedirs("exports/debug", exist_ok=True)
                output_path = f"exports/debug/test_{Path(image_path).stem}_{mode}_{upscale}x.png"
                cv2.imwrite(output_path, processed)
                print(f"  Saved to: {output_path}")
                
            except Exception as e:
                print(f"  Error: {e}")
    
    return img_bytes


def test_yolo_roi_detection(image_bytes):
    """Test YOLO ROI detection."""
    print(f"\n=== Testing YOLO ROI Detection ===")
    
    try:
        start_time = time.time()
        roi_crops = detect_serial_regions(image_bytes, padding=0.15)
        detection_time = time.time() - start_time
        
        print(f"  Detection time: {detection_time:.2f}s")
        print(f"  Number of ROI regions: {len(roi_crops)}")
        
        # Save ROI crops
        os.makedirs("exports/debug/roi", exist_ok=True)
        for i, crop in enumerate(roi_crops):
            crop_path = f"exports/debug/roi/roi_{i}.png"
            cv2.imwrite(crop_path, crop)
            print(f"  ROI {i}: shape {crop.shape}, saved to {crop_path}")
        
        return roi_crops
        
    except Exception as e:
        print(f"  Error: {e}")
        return []


def test_ocr_inference(processed_image, test_name="test"):
    """Test OCR inference on processed image."""
    print(f"\n=== Testing OCR Inference ===")
    
    try:
        # Test different OCR parameters
        low_text_values = [0.1, 0.2, 0.3]
        text_threshold_values = [0.3, 0.4, 0.5]
        mag_ratio_values = [1.0, 1.2, 1.5]
        
        best_results = []
        
        for low_text in low_text_values:
            for text_threshold in text_threshold_values:
                for mag_ratio in mag_ratio_values:
                    print(f"\n--- OCR Params: low_text={low_text}, text_threshold={text_threshold}, mag_ratio={mag_ratio} ---")
                    
                    try:
                        start_time = time.time()
                        results = _read_serials_from_image(
                            processed_image,
                            min_confidence=0.0,
                            low_text=low_text,
                            text_threshold=text_threshold,
                            mag_ratio=mag_ratio
                        )
                        ocr_time = time.time() - start_time
                        
                        print(f"  OCR time: {ocr_time:.2f}s")
                        print(f"  Results: {len(results)} candidates")
                        
                        for serial, conf in results[:3]:  # Show top 3
                            print(f"    {serial} (confidence: {conf:.3f})")
                        
                        # Track best results
                        if results:
                            best_results.extend(results)
                            
                    except Exception as e:
                        print(f"  Error: {e}")
        
        # Return unique best results
        if best_results:
            unique_results = {}
            for serial, conf in best_results:
                if serial not in unique_results or conf > unique_results[serial]:
                    unique_results[serial] = conf
            
            best_results = [(s, c) for s, c in unique_results.items()]
            best_results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"\n  Best unique results: {len(best_results)}")
            for serial, conf in best_results[:5]:
                print(f"    {serial} (confidence: {conf:.3f})")
        
        return best_results
        
    except Exception as e:
        print(f"  Error: {e}")
        return []


def test_post_processing(ocr_results):
    """Test post-processing steps."""
    print(f"\n=== Testing Post-Processing ===")
    
    if not ocr_results:
        print("  No OCR results to process")
        return []
    
    try:
        # Test character disambiguation
        print(f"\n--- Character Disambiguation ---")
        
        for serial, conf in ocr_results[:3]:  # Test first 3 results
            print(f"\n  Original: {serial} (confidence: {conf:.3f})")
            
            # Test position-aware normalization
            normalized = _normalize_ambiguous(serial, position_aware=True)
            print(f"    Position-aware normalized: {normalized}")
            
            # Test general normalization
            normalized_general = _normalize_ambiguous(serial, position_aware=False)
            print(f"    General normalized: {normalized_general}")
            
            # Test ambiguity expansion
            variants = _expand_ambiguous(serial, position_aware=True)
            print(f"    Position-aware variants: {len(variants)}")
            for i, variant in enumerate(list(variants)[:5]):  # Show first 5
                print(f"      {i+1}. {variant}")
            
            # Test Apple serial validation
            is_valid = is_valid_apple_serial(serial)
            print(f"    Valid Apple serial: {is_valid}")
            
            # Test normalized validation
            is_valid_norm = is_valid_apple_serial(normalized)
            print(f"    Valid normalized: {is_valid_norm}")
    
    except Exception as e:
        print(f"  Error: {e}")
    
    return ocr_results


def test_text_orientation_detection(image_path):
    """Test text orientation detection."""
    print(f"\n=== Testing Text Orientation Detection ===")
    
    try:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error: Could not read image {image_path}")
            return
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Test orientation detection
        start_time = time.time()
        orientation = _detect_text_orientation(gray)
        detection_time = time.time() - start_time
        
        print(f"  Detection time: {detection_time:.3f}s")
        print(f"  Detected orientation: {orientation}°")
        
        # Test smart rotation angles
        smart_angles = _get_smart_rotation_angles(gray, fine_rotation=False)
        print(f"  Smart rotation angles (no fine): {smart_angles}")
        
        smart_angles_fine = _get_smart_rotation_angles(gray, fine_rotation=True)
        print(f"  Smart rotation angles (with fine): {smart_angles_fine}")
        
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test full OCR pipeline")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--preset", default="apple_silicon", help="Preset to use")
    args = parser.parse_args()
    
    print(f"Testing full OCR pipeline on: {args.image}")
    print(f"Using preset: {args.preset}")
    
    # Create debug directory
    os.makedirs("exports/debug", exist_ok=True)
    
    # Test 1: Preprocessing
    img_bytes = test_preprocessing(args.image, args.preset)
    if img_bytes is None:
        return 1
    
    # Test 2: YOLO ROI Detection
    roi_crops = test_yolo_roi_detection(img_bytes)
    
    # Test 3: OCR on full image
    # Load a processed image for testing
    test_img = cv2.imread(f"exports/debug/test_{Path(args.image).stem}_gray_3.0x.png")
    if test_img is not None:
        ocr_results = test_ocr_inference(test_img, "full_image")
        
        # Test 4: Post-processing
        final_results = test_post_processing(ocr_results)
    else:
        print("\nSkipping OCR test - no processed image found")
    
    # Test 5: Text orientation detection
    test_text_orientation_detection(args.image)
    
    print(f"\n=== Test Complete ===")
    print(f"Check exports/debug/ for all output files")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
