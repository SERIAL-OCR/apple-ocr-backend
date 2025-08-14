#!/usr/bin/env python3
"""
Train a YOLOv5 nano model for Apple serial number region detection.

This script:
1. Trains a YOLOv5 nano model on the prepared dataset
2. Exports the model to ONNX format for inference
3. Validates the model on the test set

Usage:
    python train_yolo_model.py --data data/serial_detector/data.yaml --epochs 30 --batch 16
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from ultralytics import YOLO
except ImportError:
    print("Error: ultralytics package not found. Please install with 'pip install ultralytics'")
    sys.exit(1)
except Exception as e:
    print(f"Error importing YOLO: {str(e)}")
    print("Continuing without YOLO training capabilities. You can still use the OCR pipeline.")
    YOLO = None


def train_yolo_model(
    data_yaml: str,
    epochs: int = 30,
    batch_size: int = 16,
    image_size: int = 640,
    model_type: str = "yolov5n",  # nano model
    output_dir: Optional[str] = None,
    device: str = "",  # Auto-select device
):
    """Train a YOLOv5 model for serial number region detection."""
    if YOLO is None:
        print("YOLO training is not available. Please check your installation.")
        return None
    """
    Train a YOLOv5 model for serial number region detection.
    
    Args:
        data_yaml: Path to data.yaml configuration file
        epochs: Number of training epochs
        batch_size: Batch size
        image_size: Input image size
        model_type: YOLOv5 model type (yolov5n, yolov5s, etc.)
        output_dir: Output directory for trained model
        device: Device to use (cuda, cpu, or empty for auto-select)
    """
    # Set output directory
    if output_dir is None:
        output_dir = os.path.join("models", "serial_detector")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Training YOLOv5 model with the following parameters:")
    print(f"  Data: {data_yaml}")
    print(f"  Model: {model_type}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Image size: {image_size}")
    print(f"  Output directory: {output_dir}")
    
    # Load a model
    model = YOLO(f"{model_type}.pt")  # load a pretrained model
    
    # Train the model
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=image_size,
        batch=batch_size,
        device=device,
        project=output_dir,
        name="train",
    )
    
    # Evaluate on the validation set
    val_results = model.val()
    print(f"Validation results: {val_results}")
    
    # Export to ONNX
    onnx_path = os.path.join(output_dir, f"{model_type}_serial_detector.onnx")
    model.export(format="onnx", imgsz=image_size)
    
    print(f"Model exported to ONNX: {onnx_path}")
    print(f"Training complete. Model saved to {output_dir}")
    
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv5 model for Apple serial number detection")
    parser.add_argument("--data", required=True, help="Path to data.yaml configuration file")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--img-size", type=int, default=640, help="Input image size")
    parser.add_argument("--model", default="yolov5n", help="YOLOv5 model type (yolov5n, yolov5s, etc.)")
    parser.add_argument("--output", help="Output directory for trained model")
    parser.add_argument("--device", default="", help="Device to use (cuda, cpu, or empty for auto-select)")
    parser.add_argument("--skip-on-error", action="store_true", help="Skip training on error instead of failing")
    
    args = parser.parse_args()
    
    try:
        train_yolo_model(
            data_yaml=args.data,
            epochs=args.epochs,
            batch_size=args.batch,
            image_size=args.img_size,
            model_type=args.model,
            output_dir=args.output,
            device=args.device,
        )
    except Exception as e:
        print(f"Error during YOLO training: {str(e)}")
        if not args.skip_on_error:
            sys.exit(1)
        else:
            print("Skipping YOLO training due to error. Continuing with OCR pipeline.")
            # Create model directory to avoid future errors
            if args.output:
                os.makedirs(args.output, exist_ok=True)


if __name__ == "__main__":
    main()
