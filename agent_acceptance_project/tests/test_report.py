"""Tests for the report module."""
import unittest

from report import incomplete_count
from task_store import TaskStore


class ReportTests(unittest.TestCase):
    def test_incomplete_count_of_empty_store_is_zero(self):
        store = TaskStore()
        self.assertEqual(incomplete_count(store), 0)

    def test_incomplete_count_matches_open_tasks(self):
        # BUG: off-by-one makes the count equal to len + 1.
        store = TaskStore()
        store.add("task a")
        store.add("task b")
        self.assertEqual(incomplete_count(store), 2)

    def test_incomplete_count_after_completion(self):
        store = TaskStore()
        store.add("task a")
        store.add("task b")
        store.complete("task a")
        self.assertEqual(incomplete_count(store), 1)


if __name__ == "__main__":
    unittest.main()
