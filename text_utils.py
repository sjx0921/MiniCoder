"""Text helpers for the MiniCoder video demonstration."""


def normalize_text(text: str | None) -> str | None:
    """Normalize a text value while preserving None."""
    if text is None:
        return None
    return text.strip()
