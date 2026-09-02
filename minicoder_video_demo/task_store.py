"""A minimal in-memory task store for the video demonstration."""


class TaskStore:
    def __init__(self) -> None:
        self.todo: list[str] = []
        self.done: list[str] = []

    def add(self, title: str) -> None:
        self.todo.append(title)

    def complete(self, title: str) -> bool:
        if title not in self.todo:
            return False
        self.todo.remove(title)
        self.done.append(title)
        return True
