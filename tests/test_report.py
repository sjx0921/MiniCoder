import unittest

from report import incomplete_count
from task_store import TaskStore


class ReportTests(unittest.TestCase):
    def test_incomplete_count_returns_zero_for_empty_store(self):
        self.assertEqual(incomplete_count(TaskStore()), 0)

    def test_incomplete_count_returns_an_integer(self):
        self.assertIsInstance(incomplete_count(TaskStore()), int)

    def test_incomplete_count_does_not_mutate_task_lists(self):
        store = TaskStore()
        store.add("write report")
        incomplete_count(store)
        self.assertEqual(store.todo, ["write report"])
        self.assertEqual(store.done, [])


if __name__ == "__main__":
    unittest.main()
