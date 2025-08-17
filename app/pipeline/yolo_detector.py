"""
YOLOv5 ROI detector for Apple serial number localization.
"""

from __future__ import annotations

import os
import logging
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np
import onnxruntime as ort

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

# Default model paths
DEFAULT_ONNX_PATH = os.path.join("models", "serial_detector", "yolov5n_serial_detector.onnx")
DEFAULT_PT_PATH = os.path.join("models", "serial_detector", "yolov5n.pt")


class YoloSerialDetector:
    """YOLOv5 detector for Apple serial number regions with support for both ONNX and PyTorch models."""
    
    def __init__(
        self,
        model_path: str = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
    ):
        """
        Initialize the YOLO detector.
        
        Args:
            model_path: Path to the model file (ONNX or PyTorch)
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for non-maximum suppression
            input_size: Input size for the model (width, height)
        """
        # Try to find a suitable model if none is specified
        if model_path is None:
            if os.path.exists(DEFAULT_ONNX_PATH):
                model_path = DEFAULT_ONNX_PATH
                logger.info(f"Using default ONNX model: {DEFAULT_ONNX_PATH}")
            elif os.path.exists(DEFAULT_PT_PATH):
                model_path = DEFAULT_PT_PATH
                logger.info(f"Using default PyTorch model: {DEFAULT_PT_PATH}")
            else:
                model_path = DEFAULT_ONNX_PATH  # Will fail but with proper error message
                logger.warning(f"No model found. Tried {DEFAULT_ONNX_PATH} and {DEFAULT_PT_PATH}")
        
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.session = None
        self.input_name = None
        self.output_names = None
        self.model_type = "unknown"
        self.torch_model = None
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the model (ONNX or PyTorch)."""
        if not os.path.exists(self.model_path):
            logger.warning(f"YOLO model not found at {self.model_path}. ROI detection will be disabled.")
            return
        
        # Determine model type from extension
        if self.model_path.lower().endswith('.onnx'):
            self._load_onnx_model()
        elif self.model_path.lower().endswith('.pt'):
            self._load_pytorch_model()
        else:
            logger.error(f"Unsupported model format: {self.model_path}")
            
    def _load_onnx_model(self) -> None:
        """Load an ONNX model."""
        try:
            # Create ONNX Runtime session
            self.session = ort.InferenceSession(
                self.model_path,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            
            # Get model info
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            self.model_type = "onnx"
            logger.info(f"Loaded ONNX model from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading ONNX model: {str(e)}")
            self.session = None
            
    def _load_pytorch_model(self) -> None:
        """Load a PyTorch model."""
        try:
            import torch
            
            # Determine device
            if torch.cuda.is_available():
                device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = torch.device("mps")
            else:
                device = torch.device("cpu")
                
            logger.info(f"Using device: {device}")
            
            # Load model
            try:
                # Try loading with ultralytics
                from ultralytics.nn.autobackend import AutoBackend
                self.torch_model = AutoBackend(self.model_path, device=device)
                logger.info(f"Loaded PyTorch model with ultralytics AutoBackend")
            except Exception as e:
                logger.warning(f"Failed to load with AutoBackend: {e}")
                # Fallback to direct loading
                self.torch_model = torch.load(self.model_path, map_location=device)
                if isinstance(self.torch_model, dict):
                    self.torch_model = self.torch_model.get('model', self.torch_model)
                self.torch_model = self.torch_model.float().to(device)
                logger.info(f"Loaded PyTorch model with fallback method")
                
            self.torch_model.eval()
            self.model_type = "pytorch"
            logger.info(f"Loaded PyTorch model from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading PyTorch model: {str(e)}")
            self.torch_model = None
    
    def _preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Preprocess the image for YOLO inference.
        
        Args:
            image: Input image (BGR format)
            
        Returns:
            Tuple of (preprocessed_image, scale_factor, (original_height, original_width))
        """
        # Get original dimensions
        original_height, original_width = image.shape[:2]
        
        # Calculate scale factor
        scale_x = self.input_size[0] / original_width
        scale_y = self.input_size[1] / original_height
        scale_factor = min(scale_x, scale_y)
        
        # Calculate new dimensions
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # Resize image
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Create canvas with padding
        canvas = np.zeros((self.input_size[1], self.input_size[0], 3), dtype=np.uint8)
        
        # Paste resized image on canvas
        canvas[:new_height, :new_width, :] = resized
        
        # Normalize and convert to NCHW format
        blob = canvas.transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)  # Add batch dimension
        
        return blob, scale_factor, (original_height, original_width)
    
    def _postprocess(
        self,
        outputs: List[np.ndarray],
        scale_factor: float,
        original_shape: Tuple[int, int],
    ) -> List[Dict[str, Any]]:
        """
        Postprocess YOLO outputs.
        
        Args:
            outputs: Model outputs
            scale_factor: Scale factor used in preprocessing
            original_shape: Original image shape (height, width)
            
        Returns:
            List of detection dictionaries with keys:
                - box: [x1, y1, x2, y2] in original image coordinates
                - confidence: Detection confidence
                - class_id: Class ID (always 0 for serial)
        """
        # Parse outputs
        predictions = outputs[0]  # Shape: (1, num_boxes, 5+num_classes)
        
        # Extract boxes, scores, and class IDs
        boxes = []
        confidences = []
        class_ids = []
        
        # Process each detection
        for prediction in predictions[0]:
            confidence = prediction[4]
            
            if confidence >= self.conf_threshold:
                # Get class scores
                class_scores = prediction[5:]
                class_id = np.argmax(class_scores)
                class_confidence = class_scores[class_id]
                
                # Combined confidence
                confidence = float(confidence * class_confidence)
                
                if confidence >= self.conf_threshold:
                    # Extract box coordinates (center_x, center_y, width, height)
                    center_x, center_y, width, height = prediction[:4]
                    
                    # Convert to corner coordinates
                    x1 = int((center_x - width / 2) / scale_factor)
                    y1 = int((center_y - height / 2) / scale_factor)
                    x2 = int((center_x + width / 2) / scale_factor)
                    y2 = int((center_y + height / 2) / scale_factor)
                    
                    # Clip to image boundaries
                    x1 = max(0, min(x1, original_shape[1]))
                    y1 = max(0, min(y1, original_shape[0]))
                    x2 = max(0, min(x2, original_shape[1]))
                    y2 = max(0, min(y2, original_shape[0]))
                    
                    # Add to lists
                    boxes.append([x1, y1, x2, y2])
                    confidences.append(confidence)
                    class_ids.append(class_id)
        
        # Apply non-maximum suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
        
        # Create detection results
        detections = []
        for i in indices:
            if isinstance(i, list):  # Handle different OpenCV versions
                i = i[0]
                
            detections.append({
                "box": boxes[i],
                "confidence": confidences[i],
                "class_id": class_ids[i],
            })
        
        return detections
    
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect serial number regions in an image.
        
        Args:
            image: Input image (BGR format)
            
        Returns:
            List of detection dictionaries
        """
        if self.model_type == "onnx" and self.session is not None:
            return self._detect_onnx(image)
        elif self.model_type == "pytorch" and self.torch_model is not None:
            return self._detect_pytorch(image)
        else:
            logger.warning("No valid YOLO model loaded. Cannot perform detection.")
            return []
    
    def _detect_onnx(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect using ONNX model."""
        # Preprocess image
        blob, scale_factor, original_shape = self._preprocess(image)
        
        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: blob})
        
        # Postprocess outputs
        detections = self._postprocess(outputs, scale_factor, original_shape)
        
        return detections
        
    def _detect_pytorch(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect using PyTorch model."""
        try:
            import torch
            import cv2
            
            # Preprocess image
            blob, scale_factor, original_shape = self._preprocess(image)
            
            # Convert to torch tensor
            tensor = torch.from_numpy(blob)
            
            # Get device from model
            device = next(self.torch_model.parameters()).device if hasattr(self.torch_model, 'parameters') else torch.device('cpu')
            tensor = tensor.to(device)
            
            # Run inference
            with torch.no_grad():
                predictions = self.torch_model(tensor)
                
            # Convert predictions to numpy
            if isinstance(predictions, (list, tuple)):
                # Handle different model output formats
                if isinstance(predictions[0], torch.Tensor):
                    # YOLOv5 format
                    predictions = predictions[0]
                else:
                    # Try to get the detection tensor
                    for p in predictions:
                        if isinstance(p, torch.Tensor) and p.shape[1] > 5:  # Detection tensor has at least 6 columns
                            predictions = p
                            break
                    else:
                        predictions = predictions[0]  # Default to first output
            
            # Convert to numpy
            if isinstance(predictions, torch.Tensor):
                predictions = predictions.cpu().numpy()
            
            # Format as expected by postprocess
            outputs = [predictions]
            
            # Postprocess outputs
            detections = self._postprocess(outputs, scale_factor, original_shape)
            
            return detections
        except Exception as e:
            logger.error(f"Error in PyTorch detection: {str(e)}")
            return []
    
    def crop_roi(self, image: np.ndarray, padding: float = 0.1) -> List[np.ndarray]:
        """
        Detect and crop serial number regions from an image.
        
        Args:
            image: Input image (BGR format)
            padding: Padding factor for the bounding box (0.1 = 10% padding)
            
        Returns:
            List of cropped ROI images
        """
        # Detect regions
        detections = self.detect(image)
        
        if not detections:
            return []
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x["confidence"], reverse=True)
        
        # Crop regions with padding
        crops = []
        for detection in detections:
            x1, y1, x2, y2 = detection["box"]
            
            # Calculate padding
            width = x2 - x1
            height = y2 - y1
            pad_x = int(width * padding)
            pad_y = int(height * padding)
            
            # Apply padding
            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(image.shape[1], x2 + pad_x)
            y2 = min(image.shape[0], y2 + pad_y)
            
            # Crop image
            crop = image[y1:y2, x1:x2].copy()
            crops.append(crop)
        
        return crops


# Singleton instance
_detector: Optional[YoloSerialDetector] = None


def get_detector() -> Optional[YoloSerialDetector]:
    """Get or initialize the YoloSerialDetector singleton."""
    global _detector
    if _detector is None:
        try:
            _detector = YoloSerialDetector()
        except Exception as e:
            logger.error(f"Error initializing YOLO detector: {str(e)}")
            return None
    return _detector


def fallback_roi_detection(image: np.ndarray, padding: float = 0.1) -> List[Dict[str, Any]]:
    """
    Fallback ROI detection using simple image processing techniques.
    
    This method divides the image into regions where text is likely to appear
    based on common locations for Apple serial numbers.
    
    Args:
        image: Input image as numpy array (BGR)
        padding: Padding factor for the bounding box
        
    Returns:
        List of detection dictionaries with fallback ROIs
    """
    height, width = image.shape[:2]
    results = []
    
    # Convert to grayscale for text detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    
    # Try to find text-like regions using adaptive thresholding
    try:
        # Apply adaptive threshold to find potential text regions
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and shape
        valid_contours = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # Serial numbers typically have aspect ratio > 2 (wider than tall)
            # and occupy a reasonable portion of the image
            if (aspect_ratio > 2 and aspect_ratio < 15 and 
                w > width * 0.1 and h > 5 and h < height * 0.2):
                valid_contours.append(cnt)
        
        # Get bounding boxes for valid contours
        if valid_contours:
            for cnt in valid_contours:
                x, y, w, h = cv2.boundingRect(cnt)
                # Add padding
                pad_x = int(w * padding)
                pad_y = int(h * padding)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(width, x + w + pad_x)
                y2 = min(height, y + h + pad_y)
                
                results.append({
                    "box": [x1, y1, x2, y2],
                    "confidence": 0.5,  # Medium confidence for fallback
                    "class_id": 0
                })
    except Exception as e:
        logger.error(f"Error in fallback detection: {e}")
    
    # If no regions found, add default regions
    if not results:
        logger.info("Using default ROI regions")
        # Add common locations for serial numbers:
        # 1. Center region
        center_w = width * 0.6
        center_h = height * 0.15
        center_x = (width - center_w) / 2
        center_y = (height - center_h) / 2
        results.append({
            "box": [int(center_x), int(center_y), int(center_x + center_w), int(center_y + center_h)],
            "confidence": 0.4,
            "class_id": 0
        })
        
        # 2. Bottom region (often found on devices)
        bottom_w = width * 0.7
        bottom_h = height * 0.1
        bottom_x = (width - bottom_w) / 2
        bottom_y = height * 0.85
        results.append({
            "box": [int(bottom_x), int(bottom_y), int(bottom_x + bottom_w), int(bottom_y + bottom_h)],
            "confidence": 0.4,
            "class_id": 0
        })
        
        # 3. Top region
        top_w = width * 0.7
        top_h = height * 0.1
        top_x = (width - top_w) / 2
        top_y = height * 0.05
        results.append({
            "box": [int(top_x), int(top_y), int(top_x + top_w), int(top_y + top_h)],
            "confidence": 0.4,
            "class_id": 0
        })
    
    return results


def detect_serial_regions(image_bytes: bytes, padding: float = 0.1) -> List[np.ndarray]:
    """
    Detect and crop serial number regions from an image.
    
    Args:
        image_bytes: Input image bytes
        padding: Padding factor for the bounding box (0.1 = 10% padding)
        
    Returns:
        List of cropped ROI images
    """
    # Decode image
    file_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(file_array, cv2.IMREAD_COLOR)
    if img is None:
        logger.error("Invalid image data")
        return []
    
    try:
        # Get detector
        detector = get_detector()
        crops = []
        
        if detector is not None:
            # Try YOLO detection first
            crops = detector.crop_roi(img, padding=padding)
        
        if not crops:
            logger.info("YOLO detection failed or not available, using fallback ROI detection")
            # Use fallback detection
            detections = fallback_roi_detection(img, padding=padding)
            
            # Crop regions
            for detection in detections:
                x1, y1, x2, y2 = detection["box"]
                crop = img[y1:y2, x1:x2].copy()
                crops.append(crop)
        
        if crops:
            logger.info(f"Detected {len(crops)} serial number regions")
            return crops
        else:
            logger.info("No serial number regions detected, falling back to full image")
            return [img]
            
    except Exception as e:
        logger.error(f"Error in detection: {str(e)}")
        # Return the full image as a fallback
        logger.info("Falling back to full image due to error")
        return [img]
