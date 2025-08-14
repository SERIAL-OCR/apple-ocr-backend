#!/usr/bin/env python3
"""
Prepare a dataset for training a YOLOv5 model to detect Apple serial number regions.

This script:
1. Collects images from specified directories
2. Creates a labeling tool for annotating serial number regions
3. Generates YOLO-format annotations
4. Creates train/val/test splits
5. Prepares data.yaml configuration file

Usage:
    python prepare_yolo_dataset.py --input_dirs "Apple serial" "exports/debug_images" --output_dir "data/serial_detector"
"""

import os
import sys
import argparse
import shutil
import random
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class BoundingBoxAnnotator:
    """Simple GUI tool for annotating bounding boxes."""
    
    def __init__(self, window_name: str = "Annotator"):
        self.window_name = window_name
        self.image = None
        self.original_image = None
        self.roi_points = []
        self.dragging = False
        self.start_point = None
        self.end_point = None
        self.current_box = None
        self.boxes = []
        
    def _mouse_callback(self, event, x, y, flags, param):
        """Mouse callback for OpenCV window."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.dragging = True
            self.start_point = (x, y)
            self.current_box = None
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging:
                self.end_point = (x, y)
                # Create a copy of the original image
                self.image = self.original_image.copy()
                # Draw existing boxes
                for box in self.boxes:
                    cv2.rectangle(self.image, box[0], box[1], (0, 255, 0), 2)
                # Draw current box
                cv2.rectangle(self.image, self.start_point, self.end_point, (0, 0, 255), 2)
                cv2.imshow(self.window_name, self.image)
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
            self.end_point = (x, y)
            self.current_box = (self.start_point, self.end_point)
            self.boxes.append(self.current_box)
            
            # Draw the finalized box
            cv2.rectangle(self.image, self.start_point, self.end_point, (0, 255, 0), 2)
            cv2.imshow(self.window_name, self.image)
    
    def annotate(self, image: np.ndarray) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Annotate bounding boxes on an image.
        
        Args:
            image: Input image
            
        Returns:
            List of bounding boxes as ((x1, y1), (x2, y2))
        """
        self.original_image = image.copy()
        self.image = image.copy()
        self.boxes = []
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        
        print("\n--- Bounding Box Annotation ---")
        print("Left-click and drag to draw boxes around serial number regions")
        print("Press 'c' to clear all boxes")
        print("Press 'd' to delete the last box")
        print("Press 's' to save and continue")
        print("Press 'q' to skip this image")
        
        while True:
            cv2.imshow(self.window_name, self.image)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):  # Save
                break
            elif key == ord('c'):  # Clear all
                self.boxes = []
                self.image = self.original_image.copy()
                cv2.imshow(self.window_name, self.image)
            elif key == ord('d'):  # Delete last
                if self.boxes:
                    self.boxes.pop()
                    self.image = self.original_image.copy()
                    for box in self.boxes:
                        cv2.rectangle(self.image, box[0], box[1], (0, 255, 0), 2)
                    cv2.imshow(self.window_name, self.image)
            elif key == ord('q'):  # Skip
                self.boxes = []
                break
        
        cv2.destroyWindow(self.window_name)
        return self.boxes


def convert_to_yolo_format(boxes: List[Tuple[Tuple[int, int], Tuple[int, int]]], 
                          image_width: int, image_height: int) -> List[List[float]]:
    """
    Convert OpenCV format boxes to YOLO format.
    
    Args:
        boxes: List of boxes in ((x1, y1), (x2, y2)) format
        image_width: Width of the image
        image_height: Height of the image
        
    Returns:
        List of boxes in YOLO format [class_id, x_center, y_center, width, height]
    """
    yolo_boxes = []
    
    for box in boxes:
        # Extract coordinates
        (x1, y1), (x2, y2) = box
        
        # Ensure x1 < x2 and y1 < y2
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Calculate YOLO format (normalized)
        x_center = (x1 + x2) / 2 / image_width
        y_center = (y1 + y2) / 2 / image_height
        width = (x2 - x1) / image_width
        height = (y2 - y1) / image_height
        
        # Class ID 0 for "serial"
        yolo_boxes.append([0, x_center, y_center, width, height])
    
    return yolo_boxes


def prepare_dataset(input_dirs: List[str], output_dir: str, split_ratio: Tuple[float, float, float] = (0.7, 0.2, 0.1)):
    """
    Prepare a YOLOv5 dataset from input directories.
    
    Args:
        input_dirs: List of input directories containing images
        output_dir: Output directory for the dataset
        split_ratio: Train/val/test split ratio
    """
    # Create output directory structure
    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    labels_dir = os.path.join(output_dir, "labels")
    
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(images_dir, split), exist_ok=True)
        os.makedirs(os.path.join(labels_dir, split), exist_ok=True)
    
    # Collect images
    image_files = []
    for input_dir in input_dirs:
        if os.path.exists(input_dir):
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_files.append(os.path.join(root, file))
    
    if not image_files:
        print("No images found in the input directories.")
        return
    
    print(f"Found {len(image_files)} images.")
    
    # Initialize annotator
    annotator = BoundingBoxAnnotator()
    
    # Process images
    processed_count = 0
    skipped_count = 0
    
    for img_path in image_files:
        print(f"\nProcessing {img_path} ({processed_count + 1}/{len(image_files)})")
        
        # Read image
        img = cv2.imread(img_path)
        if img is None:
            print(f"Error reading {img_path}, skipping.")
            skipped_count += 1
            continue
        
        # Get annotations
        boxes = annotator.annotate(img)
        
        if not boxes:
            print(f"No annotations for {img_path}, skipping.")
            skipped_count += 1
            continue
        
        # Convert to YOLO format
        h, w = img.shape[:2]
        yolo_boxes = convert_to_yolo_format(boxes, w, h)
        
        # Determine split (train/val/test)
        r = random.random()
        if r < split_ratio[0]:
            split = "train"
        elif r < split_ratio[0] + split_ratio[1]:
            split = "val"
        else:
            split = "test"
        
        # Save image
        img_filename = os.path.basename(img_path)
        img_dest = os.path.join(images_dir, split, img_filename)
        shutil.copy(img_path, img_dest)
        
        # Save annotations
        label_filename = os.path.splitext(img_filename)[0] + ".txt"
        label_dest = os.path.join(labels_dir, split, label_filename)
        
        with open(label_dest, "w") as f:
            for box in yolo_boxes:
                f.write(f"{int(box[0])} {box[1]} {box[2]} {box[3]} {box[4]}\n")
        
        processed_count += 1
        print(f"Saved to {split} split with {len(boxes)} annotations.")
    
    print(f"\nProcessed {processed_count} images, skipped {skipped_count}.")
    
    # Create data.yaml
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {os.path.abspath(output_dir)}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("test: images/test\n\n")
        f.write("nc: 1\n")
        f.write("names: ['serial']\n")
    
    print(f"Created dataset configuration at {yaml_path}")
    print(f"To train: yolo train data={yaml_path} epochs=30 imgsz=640")


def main():
    parser = argparse.ArgumentParser(description="Prepare YOLOv5 dataset for Apple serial number detection")
    parser.add_argument("--input_dirs", nargs="+", required=True, help="Input directories containing images")
    parser.add_argument("--output_dir", default="data/serial_detector", help="Output directory for the dataset")
    parser.add_argument("--train_ratio", type=float, default=0.7, help="Training set ratio")
    parser.add_argument("--val_ratio", type=float, default=0.2, help="Validation set ratio")
    parser.add_argument("--test_ratio", type=float, default=0.1, help="Test set ratio")
    
    args = parser.parse_args()
    
    # Normalize split ratios
    total = args.train_ratio + args.val_ratio + args.test_ratio
    train_ratio = args.train_ratio / total
    val_ratio = args.val_ratio / total
    test_ratio = args.test_ratio / total
    
    prepare_dataset(args.input_dirs, args.output_dir, (train_ratio, val_ratio, test_ratio))


if __name__ == "__main__":
    main()
