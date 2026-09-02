import tempfile
import unittest
from pathlib import Path

from runtime import describe_environment


class RuntimeTests(unittest.TestCase):
    def test_environment_contains_workspace_and_unittest_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            tests_directory = workspace / "tests"
            tests_directory.mkdir()
            (tests_directory / "test_example.py").write_text("import unittest\n", encoding="utf-8")
            text = describe_environment(workspace)
        self.assertIn("Workspace absolute path:", text)
        self.assertIn("unittest-style tests detected", text)
        self.assertIn("Shell used by run_command:", text)


if __name__ == "__main__":
    unittest.main()
