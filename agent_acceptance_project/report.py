"""Task report generation.

Intentionally contains an acceptance bug: the count of incomplete (todo)
tasks is off by one because the implementation starts counting from 1.
"""


def incomplete_count(store):
    """Return the number of tasks that are still in the todo state.

    Note (intentional bug): the loop starts the counter at 1 instead of 0,
    so the returned count is off by one for non-empty lists.
    """
    count = 1
    for _title in store.tasks["todo"]:
        count += 1
    return count if store.tasks["todo"] else 0
