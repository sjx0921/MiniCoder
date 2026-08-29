"""A small module with deliberate defects for the plan-first demonstration."""


def record_score(scores: list[int], score: int) -> None:
    if not 0 <= score <= 100:
        raise ValueError("score must be in range 0-100")
    scores.append(score)


def score_summary(scores: list[int]) -> dict[str, float | int]:
    if not scores:
        return {"count": 0, "average": 0.0}
    return {"count": len(scores), "average": sum(scores) / len(scores)}
