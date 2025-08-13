import re
from typing import Tuple, Optional

# Basic pattern: 12 alphanumeric characters
_BASIC_PATTERN = re.compile(r"^[A-Z0-9]{12}$")

# Modern Apple serial format pattern (post-2010)
# First 3: Plant code + year + week of manufacture
# Middle 5-8: Unique identifier
# Last 4: Model + configuration
_MODERN_PATTERN = re.compile(r"^[A-Z0-9]{3}[A-Z0-9]{5,8}[A-Z0-9]{4}$")

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


def is_valid_apple_serial(text: str) -> bool:
    """
    Basic validation of Apple serial number format.
    
    Args:
        text: Serial number to validate
        
    Returns:
        True if the serial number has a valid format
    """
    if not text:
        return False
    
    candidate = text.strip().upper()
    
    # Basic check: 12 alphanumeric characters
    return bool(_BASIC_PATTERN.match(candidate))


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
        # Unknown prefix, but not necessarily invalid
        pass
    
    # Check for disallowed characters that are commonly confused
    # This is a heuristic and might need adjustment based on real-world data
    disallowed_count = sum(1 for c in candidate if c in _DISALLOWED_CHARS)
    if disallowed_count > 3:  # Allow a few potentially confused characters
        return False, f"Too many potentially confused characters: {', '.join(_DISALLOWED_CHARS)}"
    
    # All checks passed
    return True, None
