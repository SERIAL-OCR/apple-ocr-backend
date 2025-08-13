"""
Unit tests for the OCR adapter module.
"""

import unittest
import os
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

from app.pipeline.ocr_adapter import (
    _normalize_ambiguous, _expand_ambiguous, _rotate_image,
    _morphological_refine, _reduce_glare
)


class TestOcrAdapter(unittest.TestCase):
    """Test cases for OCR adapter helper functions."""

    def test_normalize_ambiguous(self):
        """Test normalization of ambiguous characters."""
        self.assertEqual(_normalize_ambiguous("O1Z5B"), "01258")
        self.assertEqual(_normalize_ambiguous("OIZSBGQ"), "0125860")
        self.assertEqual(_normalize_ambiguous("ABC123"), "ABC123")
        self.assertEqual(_normalize_ambiguous(" Test "), "TEST")
    
    def test_expand_ambiguous(self):
        """Test expansion of ambiguous characters."""
        variants = _expand_ambiguous("O1")
        self.assertIn("O1", variants)
        self.assertIn("01", variants)
        
        variants = _expand_ambiguous("OIZ")
        self.assertIn("OIZ", variants)
        self.assertIn("01Z", variants)
        self.assertIn("OI2", variants)
        self.assertIn("012", variants)
    
    def test_rotate_image_90_degrees(self):
        """Test image rotation at 90-degree angles."""
        # Create a simple test image
        img = np.zeros((10, 20), dtype=np.uint8)
        img[2:8, 5:15] = 255  # White rectangle on black background
        
        # Test 90-degree rotation
        rotated = _rotate_image(img, 90)
        self.assertEqual(rotated.shape[0], 20)  # Width becomes height
        self.assertEqual(rotated.shape[1], 10)  # Height becomes width
        
        # Test 180-degree rotation
        rotated = _rotate_image(img, 180)
        self.assertEqual(rotated.shape, img.shape)  # Same shape
        
        # Test 270-degree rotation
        rotated = _rotate_image(img, 270)
        self.assertEqual(rotated.shape[0], 20)
        self.assertEqual(rotated.shape[1], 10)
        
        # Test 0/360-degree rotation (identity)
        rotated = _rotate_image(img, 0)
        self.assertEqual(rotated.shape, img.shape)
        np.testing.assert_array_equal(rotated, img)
        
        rotated = _rotate_image(img, 360)
        self.assertEqual(rotated.shape, img.shape)
        np.testing.assert_array_equal(rotated, img)
    
    def test_rotate_image_arbitrary_angles(self):
        """Test image rotation at arbitrary angles."""
        # Create a simple test image
        img = np.zeros((20, 20), dtype=np.uint8)
        img[5:15, 5:15] = 255  # White square on black background
        
        # Test arbitrary angle (45 degrees)
        rotated = _rotate_image(img, 45)
        # Check that the output is larger to accommodate the rotated content
        self.assertGreater(rotated.shape[0], img.shape[0])
        self.assertGreater(rotated.shape[1], img.shape[1])
    
    def test_morphological_refine(self):
        """Test morphological refinement."""
        # Create a simple binary image with noise
        img = np.zeros((50, 50), dtype=np.uint8)
        img[20:30, 10:40] = 255  # Main rectangle
        img[15, 15] = 255  # Noise pixel
        img[35, 35] = 255  # Noise pixel
        
        # Apply morphological refinement
        refined = _morphological_refine(img, k=2)
        
        # Check that noise is removed
        self.assertEqual(refined[15, 15], 0)
        self.assertEqual(refined[35, 35], 0)
        
        # Check that main shape is preserved
        self.assertEqual(refined[25, 25], 255)
    
    def test_reduce_glare_tophat(self):
        """Test glare reduction using top-hat method."""
        # Create a test image with simulated glare
        img = np.ones((100, 100), dtype=np.uint8) * 100  # Base gray
        img[30:70, 30:70] = 220  # Bright area (glare)
        
        # Apply top-hat glare reduction
        result = _reduce_glare(img, method="tophat")
        
        # Check that glare is reduced (bright area is less bright)
        self.assertLess(np.mean(result[30:70, 30:70]), np.mean(img[30:70, 30:70]))
    
    def test_reduce_glare_division(self):
        """Test glare reduction using division method."""
        # Create a test image with simulated glare
        img = np.ones((100, 100), dtype=np.uint8) * 100  # Base gray
        img[30:70, 30:70] = 220  # Bright area (glare)
        
        # Apply division glare reduction
        result = _reduce_glare(img, method="division")
        
        # Check that result is more uniform
        self.assertLess(np.std(result), np.std(img))
    
    def test_reduce_glare_adaptive(self):
        """Test adaptive glare reduction method selection."""
        # Create a test image with high brightness and low contrast
        bright_img = np.ones((100, 100), dtype=np.uint8) * 200
        bright_img[40:60, 40:60] = 220  # Slight variation
        
        # Create a test image with medium brightness and higher contrast
        contrast_img = np.ones((100, 100), dtype=np.uint8) * 150
        contrast_img[30:70, 30:70] = 220  # More variation
        
        with patch('app.pipeline.ocr_adapter.logger') as mock_logger:
            # Test with bright image (should select division)
            _ = _reduce_glare(bright_img, method="adaptive")
            mock_logger.debug.assert_called_with(
                "Glare Auto-selected: division (mean=200.0, std=6.0)"
            )
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Test with contrast image (should select tophat)
            _ = _reduce_glare(contrast_img, method="adaptive")
            mock_logger.debug.assert_called_with(
                "Glare Auto-selected: tophat (mean=170.0, std=33.5)"
            )


if __name__ == "__main__":
    unittest.main()
