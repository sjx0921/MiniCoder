import unittest

from task_board import add_task, complete_task, progress


class TaskBoardTests(unittest.TestCase):
    def test_add_task_normalizes_title_and_rejects_blank_input(self):
        tasks = []
        task = add_task(tasks, "  Write   tests  ")
        self.assertEqual(task, {"title": "Write tests", "done": False})
        with self.assertRaises(ValueError):
            add_task(tasks, "   ")

    def test_complete_task_ignores_title_whitespace(self):
        tasks = []
        add_task(tasks, "Read docs")
        self.assertTrue(complete_task(tasks, " Read docs "))
        self.assertTrue(tasks[0]["done"])

    def test_progress_counts_completed_and_remaining_tasks(self):
        tasks = []
        add_task(tasks, "One")
        add_task(tasks, "Two")
        complete_task(tasks, "Two")
        self.assertEqual(progress(tasks), {"total": 2, "completed": 1, "remaining": 1})


if __name__ == "__main__":
    unittest.main()
