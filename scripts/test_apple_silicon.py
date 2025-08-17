#!/usr/bin/env python3
"""
Test script for Apple Silicon MPS configuration and OCR pipeline.

This script verifies that the MPS adapter is working correctly and tests
the OCR pipeline with Apple Silicon optimized settings.
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_mps_availability():
    """Test if MPS is available and working."""
    print("=== Testing Apple Silicon MPS Availability ===")
    
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        
        # Check MPS availability
        has_mps = hasattr(torch.backends, "mps")
        mps_available = torch.backends.mps.is_available() if has_mps else False
        mps_built = torch.backends.mps.is_built() if has_mps else False
        
        print(f"MPS backend exists: {has_mps}")
        print(f"MPS available: {mps_available}")
        print(f"MPS built: {mps_built}")
        
        if mps_available and mps_built:
            print("✅ Apple Silicon MPS is available and ready to use!")
            
            # Test basic MPS operations
            try:
                device = torch.device("mps")
                x = torch.randn(3, 3).to(device)
                y = x * 2
                print("✅ Basic MPS tensor operations work")
                return True
            except Exception as e:
                print(f"❌ MPS tensor operations failed: {e}")
                return False
        else:
            print("❌ Apple Silicon MPS is not available")
            return False
            
    except ImportError:
        print("❌ PyTorch not installed")
        return False
    except Exception as e:
        print(f"❌ Error testing MPS: {e}")
        return False

def test_mps_adapter():
    """Test if the MPS adapter is working."""
    print("\n=== Testing MPS Adapter ===")
    
    try:
        import mps_adapter
        print("✅ MPS adapter imported successfully")
        
        # Check if EasyOCR is available
        try:
            import easyocr
            print("✅ EasyOCR is available")
            
            # Try to create a reader with MPS
            print("Testing EasyOCR Reader with MPS...")
            reader = easyocr.Reader(['en'], gpu=True)
            print(f"✅ EasyOCR Reader created successfully")
            print(f"   Device: {getattr(reader, 'device', 'unknown')}")
            
            return True
            
        except ImportError:
            print("⚠️ EasyOCR not installed, skipping EasyOCR test")
            return True
        except Exception as e:
            print(f"❌ EasyOCR test failed: {e}")
            return False
            
    except ImportError:
        print("❌ MPS adapter not found")
        return False
    except Exception as e:
        print(f"❌ MPS adapter test failed: {e}")
        return False

def test_ocr_pipeline(image_path=None):
    """Test the OCR pipeline with Apple Silicon preset."""
    print("\n=== Testing OCR Pipeline with Apple Silicon Preset ===")
    
    try:
        from app.config import DEVICE_PRESETS
        from app.pipeline.ocr_adapter_improved import extract_serials
        
        # Check if apple_silicon preset exists
        if "apple_silicon" not in DEVICE_PRESETS:
            print("❌ Apple Silicon preset not found in configuration")
            return False
        
        preset = DEVICE_PRESETS["apple_silicon"]
        print(f"✅ Using Apple Silicon preset: {preset.get('description', 'No description')}")
        
        # If no image provided, just test the configuration
        if not image_path:
            print("ℹ️ No image provided, skipping OCR test")
            return True
        
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return False
        
        print(f"Processing image: {image_path}")
        
        # Load image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        # Create debug directory
        debug_dir = "exports/debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Create debug path
        filename = os.path.basename(image_path)
        debug_path = os.path.join(debug_dir, f"{os.path.splitext(filename)[0]}_apple_silicon_debug")
        
        # Start timer
        start_time = time.time()
        
        # Process image with Apple Silicon preset
        results = extract_serials(
            image_bytes=image_bytes,
            debug_save_path=debug_path,
            **preset
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
        return True
        
    except Exception as e:
        print(f"❌ OCR pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Apple Silicon MPS configuration")
    parser.add_argument("--image", help="Path to test image (optional)")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR pipeline test")
    
    args = parser.parse_args()
    
    print("Apple Silicon MPS Configuration Test")
    print("=" * 50)
    
    # Test MPS availability
    mps_ok = test_mps_availability()
    
    # Test MPS adapter
    adapter_ok = test_mps_adapter()
    
    # Test OCR pipeline
    ocr_ok = True
    if not args.skip_ocr:
        ocr_ok = test_ocr_pipeline(args.image)
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"MPS Availability: {'✅ PASS' if mps_ok else '❌ FAIL'}")
    print(f"MPS Adapter: {'✅ PASS' if adapter_ok else '❌ FAIL'}")
    print(f"OCR Pipeline: {'✅ PASS' if ocr_ok else '❌ FAIL'}")
    
    if mps_ok and adapter_ok and ocr_ok:
        print("\n🎉 All tests passed! Apple Silicon MPS is configured correctly.")
        print("\nTo use Apple Silicon optimization:")
        print("1. Set environment variable: export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0")
        print("2. Use preset 'apple_silicon' in your OCR calls")
        print("3. Monitor memory usage and adjust batch_size if needed")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        print("\nTroubleshooting:")
        print("1. Ensure you're on macOS 12.3+ with Apple Silicon")
        print("2. Verify PyTorch 1.12+ is installed")
        print("3. Check that MPS is available: python -c 'import torch; print(torch.backends.mps.is_available())'")

if __name__ == "__main__":
    main()
