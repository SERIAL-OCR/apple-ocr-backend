import os
import sys
import csv
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration
API_URL = "http://localhost:8000/process-serial"
IMAGE_DIR = "Apple serial"
OUTPUT_CSV = "reports/real_images_results.csv"
DEBUG_DIR = "exports/debug/real_images"

# Create debug directory
os.makedirs(DEBUG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# Test parameters
PARAMS = {
    "min_confidence": 0.0,  # We'll filter later
    "debug_save": True,
    "persist": False,
    "preset": "etched",
    "upscale_scale": 5.0,
    "mode": "gray",
    "roi": False,
    "roi_top_k": 3,
    "adaptive_pad": True,
    "glare_reduction": "division",
    "fine_rotation": True,  # Enable fine-grained rotation angles
    "rotations": "0,90,180,270",  # Standard rotations
    "keyword_crop": True,
    "zoom_strips": 3,
}

def process_image(image_path: str) -> Tuple[bool, float, Optional[str]]:
    """Process a single image through the OCR API."""
    try:
        # Prepare the file for upload
        with open(image_path, "rb") as f:
            files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
            
            # Send the request
            response = requests.post(
                API_URL,
                files=files,
                params=PARAMS,
                timeout=90  # Longer timeout for fine-grained rotations
            )
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Error processing {image_path}: {response.status_code} - {response.text}")
                return False, 0.0, None
            
            # Parse the response
            result = response.json()
            
            # Check if any serials were detected
            if not result.get("serials"):
                print(f"No serials found in {image_path}")
                return False, 0.0, None
            
            # Get the top result
            top_serial = result["serials"][0]
            print(f"Found serial: {top_serial['serial']} with confidence {top_serial['confidence']:.2f} in {image_path}")
            return True, top_serial["confidence"], top_serial["serial"]
            
    except Exception as e:
        print(f"Exception processing {image_path}: {e}")
        return False, 0.0, None

def main():
    # Get all image files
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    # Process each image
    results = []
    success_count = 0
    
    for img_file in image_files:
        img_path = os.path.join(IMAGE_DIR, img_file)
        print(f"Processing {img_path}...")
        
        success, confidence, serial = process_image(img_path)
        
        results.append({
            "filename": img_file,
            "success": success,
            "confidence": confidence,
            "detected_serial": serial
        })
        
        if success:
            success_count += 1
    
    # Calculate success rate
    total_images = len(image_files)
    success_rate = (success_count / total_images) * 100 if total_images > 0 else 0
    
    print(f"\nProcessed {total_images} images")
    print(f"Successfully detected serials in {success_count} images ({success_rate:.1f}%)")
    
    # Write results to CSV
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = ['filename', 'success', 'confidence', 'detected_serial']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
