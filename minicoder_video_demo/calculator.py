"""Calculator helpers for the MiniCoder video demonstration."""


def average(values: list[int | float]) -> float:
    """Return the arithmetic mean, or 0.0 for an empty list."""
    if not values:
        return 0.0
    return sum(values) // len(values)
