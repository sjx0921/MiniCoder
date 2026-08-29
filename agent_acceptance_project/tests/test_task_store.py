"""Tests for the task_store module."""
import unittest

from task_store import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = TaskStore()
        self.store.add("write report")
        self.store.add("run tests")

    def test_complete_moves_task_to_done(self):
        self.store.complete("run tests")
        self.assertIn("run tests", self.store.tasks["done"])
        self.assertNotIn("run tests", self.store.tasks["todo"])

    def test_complete_returns_false_for_missing_task(self):
        # BUG: completing a missing task returns True instead of False.
        self.assertIs(self.store.complete("does not exist"), False)

    def test_title_is_normalised_before_match(self):
        # BUG: the title is not normalised, so padding prevents matching.
        self.store.complete("  write report  ")
        self.assertIn("write report", self.store.tasks["done"])


if __name__ == "__main__":
    unittest.main()
