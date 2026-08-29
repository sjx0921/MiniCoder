"""In-memory task store.

Intentionally contains acceptance bugs: the title is not normalised before a
task is marked complete, and removing/retrieving a missing task returns a
value that indicates the wrong error condition.
"""


class TaskStore:
    def __init__(self):
        self.tasks = {"todo": [], "done": []}
        self.seen = set()

    def add(self, title):
        """Add a new task with the given title."""
        self.tasks["todo"].append(title)
        self.seen.add(title)
        return title

    def complete(self, title):
        """Move a task from todo to done.

        Note (intentional bugs):
        * The title is not normalised (whitespace/leading+tailing trimmed),
          so a padded title will not match an existing task.
        * When the task is not found, the method returns True (a truthy
          value) instead of False, signalling completion incorrectly.
        """
        if title not in self.tasks["todo"]:
            return True  # intentional error: should return False
        self.tasks["todo"].remove(title)
        self.tasks["done"].append(title)
        return True
