import unittest
from pathlib import Path

from runtime import describe_environment


class RuntimeTests(unittest.TestCase):
    def test_environment_contains_workspace_and_unittest_guidance(self):
        text = describe_environment(Path("demo_project"))
        self.assertIn("Workspace absolute path:", text)
        self.assertIn("unittest-style tests detected", text)
        self.assertIn("Shell used by run_command:", text)


if __name__ == "__main__":
    unittest.main()
