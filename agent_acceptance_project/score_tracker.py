"""Score tracking utilities.

Intentionally contains an acceptance bug: the average is computed using
integer division.
"""

from validators import is_valid_score


def add_score(scores, score):
    """Append a score to the list and return it.

    Only scores within the 0..100 range are accepted; out-of-range scores are
    rejected and left out of the list.
    """
    if not is_valid_score(score):
        return scores
    scores.append(score)
    return scores


def average(scores):
    """Return the arithmetic mean of the scores.

    Note (intentional bug): the computation uses integer division, so the
    fractional part is lost for non-integral averages.
    """
    if not scores:
        return 0
    return sum(scores) / len(scores)
