"""
Smoke tests for the API endpoints.

This script tests basic functionality of the API endpoints.
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Constants
API_URL = "http://localhost:8000"
SAMPLE_IMAGE = "Apple serial/IMG-20250813-WA0024.jpg"  # Update with a valid sample image path


def test_health_endpoint():
    """Test the /health endpoint."""
    print("\n=== Testing /health endpoint ===")
    
    response = requests.get(f"{API_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check successful: {json.dumps(data, indent=2)}")
        
        # Check GPU info
        gpu_info = data.get("gpu", {})
        if gpu_info.get("cuda_available"):
            print(f"ℹ️ GPU detected: CUDA {gpu_info.get('cuda_version')}")
            print(f"ℹ️ Device count: {gpu_info.get('device_count')}")
            print(f"ℹ️ Using GPU: {gpu_info.get('use_gpu_config')}")
        else:
            print("ℹ️ No GPU detected or not available")
        
        return True
    else:
        print(f"❌ Health check failed: {response.status_code} - {response.text}")
        return False


def test_process_serial_endpoint():
    """Test the /process-serial endpoint."""
    print("\n=== Testing /process-serial endpoint ===")
    
    # Check if sample image exists
    if not os.path.exists(SAMPLE_IMAGE):
        print(f"❌ Sample image not found: {SAMPLE_IMAGE}")
        return False
    
    # Prepare the request
    with open(SAMPLE_IMAGE, "rb") as f:
        files = {"image": (os.path.basename(SAMPLE_IMAGE), f, "image/jpeg")}
        params = {
            "min_confidence": 0.0,
            "debug_save": True,
            "persist": False,
            "preset": "default",
        }
        
        # Send the request
        response = requests.post(f"{API_URL}/process-serial", files=files, params=params)
    
    if response.status_code == 200:
        data = response.json()
        serials = data.get("serials", [])
        
        if serials:
            print(f"✅ Process serial successful: Found {len(serials)} serials")
            print(f"ℹ️ Top serial: {serials[0]['serial']} (confidence: {serials[0]['confidence']:.2f})")
            if data.get("debug"):
                print(f"ℹ️ Debug image saved to: {data['debug']}")
        else:
            print("⚠️ Process serial completed but no serials found")
        
        return True
    else:
        print(f"❌ Process serial failed: {response.status_code} - {response.text}")
        return False


def test_export_endpoint():
    """Test the /export endpoint."""
    print("\n=== Testing /export endpoint ===")
    
    response = requests.get(f"{API_URL}/export", stream=True)
    
    if response.status_code == 200:
        # Get the filename from the Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = content_disposition.split("filename=")[-1].strip('"')
        
        # Save the file
        output_path = os.path.join("storage", "exports", "test_export.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Export successful: Saved to {output_path}")
        return True
    else:
        print(f"❌ Export failed: {response.status_code} - {response.text}")
        return False


def test_params_endpoint():
    """Test the /params endpoint."""
    print("\n=== Testing /params endpoint ===")
    
    response = requests.get(f"{API_URL}/params")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Parameters endpoint successful")
        
        # Check if we have any cached presets
        presets = data.get("presets", {})
        if presets:
            print(f"ℹ️ Found {len(presets)} cached parameter presets")
            for preset, info in presets.items():
                print(f"  - {preset}: {info.get('accuracy', 0):.2%} accuracy")
        else:
            print("ℹ️ No cached parameter presets found")
        
        return True
    else:
        print(f"❌ Parameters endpoint failed: {response.status_code} - {response.text}")
        return False


def test_evaluate_endpoint():
    """Test the /evaluate endpoint."""
    print("\n=== Testing /evaluate endpoint ===")
    
    # Check if we have a directory with images and labels.csv
    test_dir = "exported-assets"
    if not os.path.exists(test_dir) or not os.path.exists(os.path.join(test_dir, "labels.csv")):
        print(f"⚠️ Skipping evaluate test: {test_dir} directory or labels.csv not found")
        return True
    
    # Count images in the directory
    image_count = len([f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if image_count == 0:
        print(f"⚠️ Skipping evaluate test: No images found in {test_dir}")
        return True
    
    print(f"ℹ️ Found {image_count} images in {test_dir}")
    
    # Send a small evaluation request (just 1-2 images for smoke test)
    params = {
        "dir": test_dir,
        "min_confidence": 0.0,
        "preset": "default",
        "mode": "gray",
    }
    
    response = requests.get(f"{API_URL}/evaluate", params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Evaluate endpoint successful")
        print(f"ℹ️ Total images: {data.get('total_images', 0)}")
        print(f"ℹ️ Hits: {data.get('hits', 0)}")
        print(f"ℹ️ Misses: {data.get('misses', 0)}")
        print(f"ℹ️ Accuracy: {data.get('accuracy', 0):.2%}")
        
        if data.get("report_csv"):
            print(f"ℹ️ Report saved to: {data.get('report_csv')}")
        
        return True
    else:
        print(f"❌ Evaluate endpoint failed: {response.status_code} - {response.text}")
        return False


def run_all_tests():
    """Run all smoke tests."""
    print("Running API smoke tests...")
    
    # Track results
    results = {
        "health": test_health_endpoint(),
        "process_serial": test_process_serial_endpoint(),
        "export": test_export_endpoint(),
        "params": test_params_endpoint(),
        "evaluate": test_evaluate_endpoint(),
    }
    
    # Print summary
    print("\n=== Test Summary ===")
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test}: {status}")
        all_passed = all_passed and passed
    
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed


if __name__ == "__main__":
    # Check if API is running
    try:
        requests.get(f"{API_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print(f"❌ API not running at {API_URL}. Please start the API before running tests.")
        sys.exit(1)
    
    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
