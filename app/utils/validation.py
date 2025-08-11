import re

_SERIAL_PATTERN = re.compile(r"^[A-Z0-9]{12}$")


def is_valid_apple_serial(text: str) -> bool:
    if not text:
        return False
    candidate = text.strip().upper()
    return bool(_SERIAL_PATTERN.match(candidate))
