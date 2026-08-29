"""Validation helpers.

Provides reusable input validators used by the project modules.
"""


def is_valid_score(score):
    """Return True if score is within the accepted 0..100 range.

    Integer and float scores within the inclusive range are considered valid.
    """
    return isinstance(score, (int, float)) and 0 <= score <= 100
