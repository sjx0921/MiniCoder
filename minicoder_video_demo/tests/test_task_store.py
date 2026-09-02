import unittest

from task_store import TaskStore


class TaskStoreTests(unittest.TestCase):
    def test_add_places_task_in_todo(self):
        store = TaskStore()
        store.add("write report")
        self.assertEqual(store.todo, ["write report"])
        self.assertEqual(store.done, [])

    def test_complete_moves_exact_title_to_done(self):
        store = TaskStore()
        store.add("write report")
        self.assertTrue(store.complete("write report"))
        self.assertEqual(store.todo, [])
        self.assertEqual(store.done, ["write report"])

    def test_complete_ignores_outer_whitespace_in_title(self):
        store = TaskStore()
        store.add("write report")
        self.assertTrue(store.complete("  write report  "))
        self.assertEqual(store.done, ["write report"])


if __name__ == "__main__":
    unittest.main()
