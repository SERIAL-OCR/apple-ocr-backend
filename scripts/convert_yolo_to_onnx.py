#!/usr/bin/env python3
"""
Convert YOLOv5 PyTorch model to ONNX format.

This script converts a YOLOv5 PyTorch model to ONNX format for use with onnxruntime.
It handles the conversion process and optimizes the model for inference.

Usage:
    python convert_yolo_to_onnx.py --input models/serial_detector/yolov5n.pt --output models/serial_detector/yolov5n_serial_detector.onnx
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import torch
    from ultralytics.nn.tasks import attempt_load_one_weight
    from ultralytics.nn.autobackend import AutoBackend
except ImportError:
    print("Error: Required packages not found. Please install with 'pip install torch ultralytics'")
    sys.exit(1)

def convert_to_onnx(
    input_model: str,
    output_model: str,
    img_size: int = 640,
    batch_size: int = 1,
    simplify: bool = True,
    opset: int = 12,
    dynamic: bool = True,
    half: bool = False,
):
    """
    Convert YOLOv5 PyTorch model to ONNX format.
    
    Args:
        input_model: Path to input PyTorch model (.pt)
        output_model: Path to output ONNX model (.onnx)
        img_size: Input image size
        batch_size: Batch size
        simplify: Whether to simplify the ONNX model
        opset: ONNX opset version
        dynamic: Whether to use dynamic axes
        half: Whether to use half precision (FP16)
    """
    print(f"Converting {input_model} to ONNX format...")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_model)
    os.makedirs(output_dir, exist_ok=True)
    
    # Load PyTorch model
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(f"Using MPS device: {device}")
    else:
        print(f"Using device: {device}")
    
    # Load the model
    try:
        model = AutoBackend(input_model, device=device, dnn=False, fp16=half)
        print(f"Loaded {input_model}")
    except Exception as e:
        print(f"Error loading model: {e}")
        try:
            # Fallback to direct loading
            model = torch.load(input_model, map_location=device)
            if isinstance(model, dict):
                model = model.get('model', model)
            model = model.float().to(device)
            model.eval()
            print(f"Loaded {input_model} using fallback method")
        except Exception as e:
            print(f"Error loading model with fallback: {e}")
            sys.exit(1)
    
    # Create dummy input
    img = torch.zeros(batch_size, 3, img_size, img_size).to(device)
    if half:
        img = img.half()
    
    # Export to ONNX
    try:
        print(f"Exporting to ONNX with opset {opset}...")
        torch.onnx.export(
            model,
            img,
            output_model,
            verbose=False,
            opset_version=opset,
            input_names=["images"],
            output_names=["output"],
            dynamic_axes={
                "images": {0: "batch", 2: "height", 3: "width"},
                "output": {0: "batch", 1: "anchors"},
            } if dynamic else None,
        )
        
        # Simplify
        if simplify:
            try:
                import onnx
                import onnxsim
                
                print(f"Simplifying ONNX model...")
                model_onnx = onnx.load(output_model)
                model_onnx, check = onnxsim.simplify(model_onnx)
                assert check, "Simplified ONNX model could not be validated"
                onnx.save(model_onnx, output_model)
                print(f"Simplified ONNX model saved to {output_model}")
            except Exception as e:
                print(f"Error simplifying ONNX model: {e}")
                print(f"Continuing with non-simplified model")
        
        print(f"ONNX export success, saved as {output_model}")
        return True
    except Exception as e:
        print(f"Error exporting to ONNX: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert YOLOv5 PyTorch model to ONNX format")
    parser.add_argument("--input", required=True, help="Path to input PyTorch model (.pt)")
    parser.add_argument("--output", required=True, help="Path to output ONNX model (.onnx)")
    parser.add_argument("--img-size", type=int, default=640, help="Input image size")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--simplify", action="store_true", help="Simplify ONNX model")
    parser.add_argument("--opset", type=int, default=12, help="ONNX opset version")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic axes")
    parser.add_argument("--half", action="store_true", help="Use half precision (FP16)")
    
    args = parser.parse_args()
    
    convert_to_onnx(
        input_model=args.input,
        output_model=args.output,
        img_size=args.img_size,
        batch_size=args.batch_size,
        simplify=args.simplify,
        opset=args.opset,
        dynamic=args.dynamic,
        half=args.half,
    )

if __name__ == "__main__":
    main()
