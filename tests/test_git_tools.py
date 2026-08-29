import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.git_tools import git_diff, git_status


class GitToolTests(unittest.TestCase):
    def test_untracked_files_are_not_reported_as_clean_or_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            (workspace / "new.txt").write_text("new", encoding="utf-8")
            self.assertIn("未跟踪条目：1", git_status(workspace))
            self.assertIn("new.txt", git_diff(workspace))


if __name__ == "__main__":
    unittest.main()
