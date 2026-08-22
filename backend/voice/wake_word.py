import re
from typing import Callable, Optional
import numpy as np

WAKE_WORD_KEYWORDS = [
    r"\bhey\s+cruz\b",
    r"\bhi\s+cruz\b",
    r"\bhello\s+cruz\b",
    r"\bok\s+cruz\b",
    r"\bokay\s+cruz\b",
    r"\bcruz\b",
    r"\bhey\s+cruise\b",
    r"\bcruise\b",
    r"\bhey\s+crews\b",
    r"\bcrews\b",
    r"\bkruz\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in WAKE_WORD_KEYWORDS]


def is_wake_word(text: str) -> bool:
    """Checks if the given transcription text matches the 'Hey Cruz' wake word."""
    if not text:
        return False
    clean = text.strip()
    return any(p.search(clean) for p in COMPILED_PATTERNS)


def extract_prompt_after_wake_word(text: str) -> Optional[str]:
    """
    Extracts the user prompt following the wake word if they spoke in a single sentence
    e.g. 'Hey Cruz what time is it' -> 'what time is it'
    """
    if not text:
        return None
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            remainder = text[match.end():].strip(" ,.?!")
            return remainder if remainder else None
    return None
