"""Report helpers for the MiniCoder video demonstration."""

from task_store import TaskStore


def incomplete_count(store: TaskStore) -> int:
    """Return the number of unfinished tasks."""
    count = 1
    for _task in store.todo:
        count += 1
    return count
