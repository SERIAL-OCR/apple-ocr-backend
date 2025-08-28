import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Validation confidence levels for client-side processing"""
    REJECT = "reject"
    BORDERLINE = "borderline"  # Requires user confirmation
    ACCEPT = "accept"


@dataclass
class ValidationResult:
    """Result of client-side validation"""
    is_valid: bool
    confidence_level: ValidationLevel
    corrected_serial: Optional[str] = None
    corrections_made: List[str] = None
    validation_notes: List[str] = None
    requires_user_confirmation: bool = False
    
    def __post_init__(self):
        if self.corrections_made is None:
            self.corrections_made = []
        if self.validation_notes is None:
            self.validation_notes = []


class AppleSerialValidator:
    """
    Advanced Apple serial number validator with position-aware disambiguation
    and confidence shaping for Phase 2.3 client-side processing.
    """
    
    # Position-specific character mappings for disambiguation
    POSITION_CORRECTIONS = {
        0: {  # First character (manufacturing location)
            '0': 'O',  # O is more common in first position
            '1': 'I',  # I is more common in first position
        },
        1: {  # Second character
            '0': 'O',
            '1': 'I',
            '5': 'S',
        },
        2: {  # Third character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        3: {  # Fourth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        4: {  # Fifth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        5: {  # Sixth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        6: {  # Seventh character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        7: {  # Eighth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        8: {  # Ninth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        9: {  # Tenth character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        10: {  # Eleventh character
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        },
        11: {  # Twelfth character (last)
            '0': 'O',
            '1': 'I',
            '5': 'S',
            '8': 'B',
        }
    }
    
    # Known Apple serial prefixes (common patterns)
    KNOWN_PREFIXES = {
        'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C0A', 'C0B', 'C0C', 'C0D', 'C0E', 'C0F',
        'CO2', 'CO3', 'CO4', 'CO5', 'CO6', 'CO7', 'CO8', 'CO9', 'COA', 'COB', 'COC', 'COD', 'COE', 'COF',  # Common OCR corrections
        'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'CA', 'CB', 'CC', 'CD', 'CE', 'CF',
        'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
    }
    
    # Position-specific patterns (what characters are expected at each position)
    POSITION_PATTERNS = {
        0: re.compile(r'[A-Z]'),  # First char should be a letter (manufacturing location)
        1: re.compile(r'[A-Z0-9]'),  # Second char can be letter or number
        2: re.compile(r'[A-Z0-9]'),  # Third char can be letter or number
        3: re.compile(r'[A-Z0-9]'),  # Fourth char can be letter or number
        4: re.compile(r'[A-Z0-9]'),  # Fifth char can be letter or number
        5: re.compile(r'[A-Z0-9]'),  # Sixth char can be letter or number
        6: re.compile(r'[A-Z0-9]'),  # Seventh char can be letter or number
        7: re.compile(r'[A-Z0-9]'),  # Eighth char can be letter or number
        8: re.compile(r'[A-Z0-9]'),  # Ninth char can be letter or number
        9: re.compile(r'[A-Z0-9]'),  # Tenth char can be letter or number
        10: re.compile(r'[A-Z0-9]'),  # Eleventh char can be letter or number
        11: re.compile(r'[A-Z0-9]'),  # Twelfth char can be letter or number
    }
    
    def __init__(self):
        self.basic_pattern = re.compile(r'^[A-Z0-9]{12}$')
    
    def validate_with_corrections(self, serial: str, confidence: float) -> ValidationResult:
        """
        Main validation method with position-aware corrections and confidence shaping.
        
        Args:
            serial: Raw serial number from OCR
            confidence: OCR confidence score (0.0-1.0)
            
        Returns:
            ValidationResult with validation status and any corrections made
        """
        if not serial:
            return ValidationResult(
                is_valid=False,
                confidence_level=ValidationLevel.REJECT,
                validation_notes=["Empty serial number"]
            )
        
        # Normalize input
        candidate = serial.strip().upper()
        
        # Basic format check
        if not self.basic_pattern.match(candidate):
            return ValidationResult(
                is_valid=False,
                confidence_level=ValidationLevel.REJECT,
                validation_notes=[f"Invalid format: must be 12 alphanumeric characters, got '{candidate}'"]
            )
        
        # Apply position-aware corrections
        corrected_serial, corrections = self._apply_position_corrections(candidate)
        
        # Validate the corrected serial
        validation_result = self._validate_corrected_serial(corrected_serial, confidence, corrections)
        
        return validation_result
    
    def _apply_position_corrections(self, serial: str) -> Tuple[str, List[str]]:
        """
        Apply position-aware character corrections based on common OCR mistakes.
        
        Args:
            serial: 12-character serial number
            
        Returns:
            Tuple of (corrected_serial, list_of_corrections_made)
        """
        corrections = []
        corrected_chars = list(serial)
        
        for pos, char in enumerate(serial):
            if pos in self.POSITION_CORRECTIONS and char in self.POSITION_CORRECTIONS[pos]:
                corrected_char = self.POSITION_CORRECTIONS[pos][char]
                corrected_chars[pos] = corrected_char
                corrections.append(f"Position {pos+1}: '{char}' → '{corrected_char}'")
        
        corrected_serial = ''.join(corrected_chars)
        return corrected_serial, corrections
    
    def _validate_corrected_serial(self, serial: str, confidence: float, corrections: List[str]) -> ValidationResult:
        """
        Validate the corrected serial number and determine confidence level.
        
        Args:
            serial: Corrected serial number
            confidence: Original OCR confidence
            corrections: List of corrections made
            
        Returns:
            ValidationResult with validation status
        """
        validation_notes = []
        requires_user_confirmation = False
        
        # Check for known prefixes
        prefix_3 = serial[:3]
        prefix_2 = serial[:2]
        prefix_1 = serial[0]
        
        has_known_prefix = (
            prefix_3 in self.KNOWN_PREFIXES or
            prefix_2 in self.KNOWN_PREFIXES or
            prefix_1 in self.KNOWN_PREFIXES
        )
        
        if has_known_prefix:
            validation_notes.append("Known Apple serial prefix detected")
        else:
            validation_notes.append("Unknown prefix - may need verification")
            requires_user_confirmation = True
        
        # Check position-specific patterns
        position_errors = []
        for pos, pattern in self.POSITION_PATTERNS.items():
            if pos < len(serial) and not pattern.match(serial[pos]):
                position_errors.append(f"Position {pos+1}: '{serial[pos]}' doesn't match expected pattern")
        
        if position_errors:
            validation_notes.extend(position_errors)
            requires_user_confirmation = True
        
        # Check for common Apple serial patterns
        # Last 4 characters should contain at least one digit
        if not any(c.isdigit() for c in serial[-4:]):
            validation_notes.append("Warning: Last 4 characters should contain at least one digit")
            requires_user_confirmation = True
        
        # Middle section should have mix of letters and numbers
        middle = serial[3:8]
        has_letter = any(c.isalpha() for c in middle)
        has_digit = any(c.isdigit() for c in middle)
        if not (has_letter and has_digit):
            validation_notes.append("Warning: Middle section should have mix of letters and numbers")
            requires_user_confirmation = True
        
        # Confidence shaping based on corrections and validation
        adjusted_confidence = self._shape_confidence(confidence, corrections, validation_notes)
        
        # Determine validation level
        if adjusted_confidence >= 0.85 and not requires_user_confirmation and has_known_prefix:
            confidence_level = ValidationLevel.ACCEPT
        elif adjusted_confidence >= 0.65 and has_known_prefix:
            confidence_level = ValidationLevel.BORDERLINE
        else:
            confidence_level = ValidationLevel.REJECT
        
        # Determine if valid
        is_valid = (
            confidence_level != ValidationLevel.REJECT and
            len(position_errors) <= 1 and  # Allow minor position errors
            has_known_prefix
        )
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_level=confidence_level,
            corrected_serial=serial if corrections else None,
            corrections_made=corrections,
            validation_notes=validation_notes,
            requires_user_confirmation=requires_user_confirmation
        )
    
    def _shape_confidence(self, original_confidence: float, corrections: List[str], validation_notes: List[str]) -> float:
        """
        Shape the confidence score based on corrections and validation results.
        
        Args:
            original_confidence: Original OCR confidence
            corrections: List of corrections made
            validation_notes: Validation notes
            
        Returns:
            Adjusted confidence score
        """
        adjusted_confidence = original_confidence
        
        # Penalty for corrections (each correction reduces confidence)
        correction_penalty = len(corrections) * 0.05
        adjusted_confidence -= correction_penalty
        
        # Penalty for validation warnings
        warning_penalty = len([note for note in validation_notes if 'Warning:' in note]) * 0.03
        adjusted_confidence -= warning_penalty
        
        # Bonus for known prefixes
        if any('Known Apple serial prefix' in note for note in validation_notes):
            adjusted_confidence += 0.10
        
        # Ensure confidence stays within bounds
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        return adjusted_confidence
    
    def should_submit_to_backend(self, validation_result: ValidationResult, user_confirmed: bool = False) -> bool:
        """
        Determine if the serial should be submitted to the backend.
        
        Args:
            validation_result: Result from validate_with_corrections
            user_confirmed: Whether user has explicitly confirmed the serial
            
        Returns:
            True if should submit to backend
        """
        if validation_result.confidence_level == ValidationLevel.REJECT:
            return False
        
        if validation_result.confidence_level == ValidationLevel.ACCEPT:
            return True
        
        # For borderline cases, require user confirmation
        if validation_result.confidence_level == ValidationLevel.BORDERLINE:
            return user_confirmed
        
        return False


# Convenience functions for easy integration
def validate_apple_serial_client(serial: str, confidence: float) -> ValidationResult:
    """
    Convenience function for client-side validation.
    
    Args:
        serial: Raw serial number from OCR
        confidence: OCR confidence score
        
    Returns:
        ValidationResult with validation status and corrections
    """
    validator = AppleSerialValidator()
    return validator.validate_with_corrections(serial, confidence)


def should_submit_serial(validation_result: ValidationResult, user_confirmed: bool = False) -> bool:
    """
    Convenience function to determine if serial should be submitted.
    
    Args:
        validation_result: Result from validate_apple_serial_client
        user_confirmed: Whether user has confirmed the serial
        
    Returns:
        True if should submit to backend
    """
    validator = AppleSerialValidator()
    return validator.should_submit_to_backend(validation_result, user_confirmed)
