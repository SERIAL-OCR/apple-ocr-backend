"""
Unit tests for the validation module.
"""

import unittest
from app.utils.validation import is_valid_apple_serial, validate_apple_serial_extended


class TestValidation(unittest.TestCase):
    """Test cases for serial number validation."""

    def test_basic_validation(self):
        """Test basic serial number validation."""
        # Valid serials
        self.assertTrue(is_valid_apple_serial("C02Y95A8JG5H"))
        self.assertTrue(is_valid_apple_serial("F5KVN0DKHJC5"))
        self.assertTrue(is_valid_apple_serial("DGKFL96JDRVG"))
        
        # Invalid serials
        self.assertFalse(is_valid_apple_serial(""))  # Empty
        self.assertFalse(is_valid_apple_serial("ABC123"))  # Too short
        self.assertFalse(is_valid_apple_serial("C02Y95A8JG5H1"))  # Too long
        self.assertFalse(is_valid_apple_serial("C02Y95A8JG5!"))  # Invalid character
        self.assertFalse(is_valid_apple_serial("C02Y95A8JG5 "))  # Space
    
    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        self.assertTrue(is_valid_apple_serial(" C02Y95A8JG5H "))  # Spaces should be stripped
        self.assertTrue(is_valid_apple_serial("\tC02Y95A8JG5H\n"))  # Other whitespace
    
    def test_case_insensitivity(self):
        """Test case insensitivity."""
        self.assertTrue(is_valid_apple_serial("c02y95a8jg5h"))  # Lowercase
        self.assertTrue(is_valid_apple_serial("C02y95A8jG5h"))  # Mixed case
    
    def test_extended_validation(self):
        """Test extended validation with more detailed checks."""
        # Valid serials with known prefixes
        valid, reason = validate_apple_serial_extended("C02Y95A8JG5H")
        self.assertTrue(valid)
        self.assertIsNone(reason)
        
        valid, reason = validate_apple_serial_extended("F5KVN0DKHJC5")
        self.assertTrue(valid)
        self.assertIsNone(reason)
        
        # Too many potentially confused characters
        valid, reason = validate_apple_serial_extended("OISZBGDTQQQQ")
        self.assertFalse(valid)
        self.assertIn("confused", reason.lower())
    
    def test_prefix_validation(self):
        """Test validation of known Apple serial number prefixes."""
        # Test with known prefixes
        for prefix in ["C02", "F5K", "G8V", "YM2"]:
            valid, _ = validate_apple_serial_extended(f"{prefix}{'A' * 9}")
            self.assertTrue(valid)
        
        # Unknown prefixes are still valid if they meet other criteria
        valid, _ = validate_apple_serial_extended("X99AAAAAAAAA")
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
