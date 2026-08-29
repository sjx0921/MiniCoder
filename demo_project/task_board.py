"""Small task-board module used to demonstrate MiniCoder."""


def add_task(tasks: list[dict], title: str) -> dict:
    """Add a task and return it."""
    normalized = " ".join(title.split())
    if not normalized:
        raise ValueError("Title must not be blank")
    task = {"title": normalized, "done": False}
    tasks.append(task)
    return task


def complete_task(tasks: list[dict], title: str) -> bool:
    """Mark the matching task complete."""
    normalized = " ".join(title.split())
    for task in tasks:
        if task["title"] == normalized:
            task["done"] = True
            return True
    return False


def progress(tasks: list[dict]) -> dict[str, int]:
    """Return task progress counters."""
    completed = sum(1 for task in tasks if task["done"])
    return {"total": len(tasks), "completed": completed, "remaining": len(tasks) - completed}
