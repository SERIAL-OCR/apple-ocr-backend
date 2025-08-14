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

logger = logging.getLogger(__name__)

# Default model path
DEFAULT_MODEL_PATH = os.path.join("models", "serial_detector", "yolov5n_serial_detector.onnx")


class YoloSerialDetector:
    """YOLOv5 detector for Apple serial number regions."""
    
    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
    ):
        """
        Initialize the YOLO detector.
        
        Args:
            model_path: Path to the ONNX model file
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for non-maximum suppression
            input_size: Input size for the model (width, height)
        """
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.session = None
        self.input_name = None
        self.output_names = None
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the ONNX model."""
        if not os.path.exists(self.model_path):
            logger.warning(f"YOLO model not found at {self.model_path}. ROI detection will be disabled.")
            return
        
        try:
            # Create ONNX Runtime session
            self.session = ort.InferenceSession(
                self.model_path,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            
            # Get model info
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            logger.info(f"Loaded YOLO model from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading YOLO model: {str(e)}")
            self.session = None
    
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
        if self.session is None:
            logger.warning("YOLO model not loaded. Cannot perform detection.")
            return []
        
        # Preprocess image
        blob, scale_factor, original_shape = self._preprocess(image)
        
        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: blob})
        
        # Postprocess outputs
        detections = self._postprocess(outputs, scale_factor, original_shape)
        
        return detections
    
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
        if detector is None:
            logger.warning("YOLO detector not available")
            return []
        
        # Detect and crop regions
        crops = detector.crop_roi(img, padding=padding)
        
        if crops:
            logger.info(f"Detected {len(crops)} serial number regions")
            return crops
        else:
            logger.info("No serial number regions detected")
            return []
            
    except Exception as e:
        logger.error(f"Error in YOLO detection: {str(e)}")
        # Return the full image as a fallback
        logger.info("Falling back to full image")
        return [img]
    
    return []
