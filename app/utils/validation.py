import re
from typing import Tuple, Optional, Dict, List, Set

# Basic pattern: 12 alphanumeric characters
_BASIC_PATTERN = re.compile(r"^[A-Z0-9]{12}$")

# Modern Apple serial format pattern (post-2010)
# First 3: Plant code + year + week of manufacture
# Middle 5-8: Unique identifier
# Last 4: Model + configuration
_MODERN_PATTERN = re.compile(r"^[A-Z0-9]{3}[A-Z0-9]{5,8}[A-Z0-9]{4}$")

# Position-specific patterns for Apple serials
_POSITION_PATTERNS: Dict[int, re.Pattern] = {
    # First position is usually a letter (manufacturing location)
    0: re.compile(r"[A-Z]"),
    
    # Second position is usually a digit (year of manufacture)
    1: re.compile(r"[0-9]"),
    
    # Third position can be letter or number (week of manufacture)
    2: re.compile(r"[A-Z0-9]"),
    
    # Last four positions often follow specific patterns for product types
    # These are more likely to be alphanumeric with more digits
    8: re.compile(r"[A-Z0-9]"),
    9: re.compile(r"[A-Z0-9]"),
    10: re.compile(r"[A-Z0-9]"),
    11: re.compile(r"[A-Z0-9]"),
}

# Common character positions in Apple serials (based on analysis)
_COMMON_CHARS_BY_POSITION: Dict[int, Set[str]] = {
    0: {'C', 'F', 'G', 'D', 'M', 'P', 'V', 'W', 'X', 'Y'},  # Common first chars (manufacturing locations)
    1: {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'},  # Year digit
    # Other positions have more variation
}

# Common Apple serial prefixes (first 3 chars)
_KNOWN_PREFIXES = {
    # Manufacturing locations
    'C': 'China',
    'F': 'Fremont, CA (USA)',
    'G': 'USA',
    'M': 'Malaysia',
    'P': 'Korea',
    'V': 'Czech Republic',
    'W': 'China',
    'X': 'USA',
    'Y': 'China',
    'DM': 'China',
    'DN': 'China',
    'FK': 'USA',
    'G8': 'USA',
    'QP': 'USA',
    'RN': 'Mexico',
    'RM': 'USA/Mexico',
    'SG': 'Singapore',
    'VM': 'Czech Republic',
    'YM': 'China',
    'C07': 'China',
    'C17': 'China',
    'C1M': 'China',
    'C2V': 'China',
    'F4N': 'USA',
    'F5K': 'USA',
    'FC7': 'USA',
    'G8V': 'USA',
    'QT4': 'Taiwan',
}

# Disallowed characters that are commonly confused
_DISALLOWED_CHARS = {
    'O', 'I', 'Z', 'S', 'B', 'Q', 'G', 'D', 'T'  # These are often confused with numbers
}

# Character substitution map for common OCR errors
_CORRECTION_MAP = {
    '0': ['O', 'D', 'Q'],
    '1': ['I', 'L', '|'],
    '2': ['Z'],
    '5': ['S'],
    '6': ['G'],
    '7': ['T'],
    '8': ['B'],
}


def get_possible_corrections(text: str) -> List[str]:
    """
    Generate possible corrections for common OCR errors in Apple serials.
    
    Args:
        text: Serial number to correct
        
    Returns:
        List of possible corrections
    """
    if not text or len(text) != 12:
        return [text]
    
    corrections = [text]
    
    # Apply position-specific corrections
    for i, char in enumerate(text):
        # First position is usually a letter
        if i == 0 and char.isdigit():
            for letter in _CORRECTION_MAP.get(char, []):
                corrections.append(letter + text[1:])
        
        # Positions 8-11 (last 4) are more likely to be digits
        if i >= 8 and char.isalpha():
            for digit in [k for k, v in _CORRECTION_MAP.items() if char in v]:
                corrections.append(text[:i] + digit + text[i+1:])
    
    return corrections


def is_valid_apple_serial(text: str, strict: bool = False) -> bool:
    """
    Basic validation of Apple serial number format.
    
    Args:
        text: Serial number to validate
        strict: Whether to apply stricter validation rules
        
    Returns:
        True if the serial number has a valid format
    """
    if not text:
        return False
    
    candidate = text.strip().upper()
    
    # Basic check: 12 alphanumeric characters
    if not _BASIC_PATTERN.match(candidate):
        return False
    
    # Apply extended validation if strict mode is enabled
    if strict:
        is_valid, _ = validate_apple_serial_extended(candidate)
        return is_valid
    
    return True


def validate_apple_serial_extended(text: str) -> Tuple[bool, Optional[str]]:
    """
    Extended validation of Apple serial number with detailed checks.
    
    Args:
        text: Serial number to validate
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if not text:
        return False, "Empty serial number"
    
    candidate = text.strip().upper()
    
    # Basic check: 12 alphanumeric characters
    if not _BASIC_PATTERN.match(candidate):
        return False, "Must be exactly 12 alphanumeric characters"
    
    # Check for known prefixes
    prefix = candidate[:3]
    if prefix[0] in _KNOWN_PREFIXES:
        # Good, known first character
        pass
    elif prefix[:2] in _KNOWN_PREFIXES:
        # Good, known first two characters
        pass
    elif prefix in _KNOWN_PREFIXES:
        # Good, known three-character prefix
        pass
    else:
        # Unknown prefix - apply stricter position-specific checks
        position_errors = []
        
        # Check first character (manufacturing location - usually a letter)
        if candidate[0] not in _COMMON_CHARS_BY_POSITION.get(0, set()):
            position_errors.append(f"Unusual first character: {candidate[0]}")
        
        # Check position-specific patterns
        for pos, pattern in _POSITION_PATTERNS.items():
            if pos < len(candidate) and not pattern.match(candidate[pos]):
                position_errors.append(f"Character at position {pos+1} doesn't match expected pattern")
        
        # If we have multiple position errors, this is likely not a valid serial
        if len(position_errors) > 2:
            return False, f"Failed position-specific checks: {', '.join(position_errors[:2])}..."
    
    # Check for disallowed characters that are commonly confused
    # This is a heuristic and might need adjustment based on real-world data
    disallowed_count = sum(1 for c in candidate if c in _DISALLOWED_CHARS)
    if disallowed_count > 3:  # Allow a few potentially confused characters
        return False, f"Too many potentially confused characters: {', '.join(_DISALLOWED_CHARS)}"
    
    # Check for common Apple serial number patterns
    # Last 4 characters often contain at least one digit
    if not any(c.isdigit() for c in candidate[-4:]):
        return False, "Last 4 characters should contain at least one digit"
    
    # Middle section (positions 3-7) often has a mix of letters and numbers
    middle = candidate[3:8]
    has_letter = any(c.isalpha() for c in middle)
    has_digit = any(c.isdigit() for c in middle)
    if not (has_letter and has_digit):
        # Not a strict error, but unusual
        pass
    
    # All checks passed
    return True, None
