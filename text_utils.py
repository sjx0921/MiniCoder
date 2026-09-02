"""Text helpers for the MiniCoder video demonstration."""

import re


def normalize_text(text: str | None) -> str | None:
    """Normalize a text value while preserving None.

Note: normalization also collapses consecutive internal whitespace to a single space.
"""
    if text is None:
        return None
    return re.sub(r"\s+", " ", text.strip())
