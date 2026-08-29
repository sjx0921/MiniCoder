"""Text normalisation utilities.

Intentionally contains an acceptance bug: leading/trailing whitespace is
removed but consecutive inner spaces are not collapsed into a single space.
"""


def normalize_text(text):
    """Trim leading/trailing whitespace and collapse runs of spaces.

    Note (intentional bug): only the outer whitespace is stripped; runs of
    consecutive inner whitespace are NOT merged into a single space.
    """
    return " ".join(text.split(" ")).strip() if text is not None else None
