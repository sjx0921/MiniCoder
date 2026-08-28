import tempfile
import unittest
from pathlib import Path

from tools.file_tools import ToolError, list_files, read_file, resolve_workspace_path, search_text, write_file
from tools.registry import ToolRegistry
from tools.shell_tool import run_command


class FileToolTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_round_trip_and_listing(self):
        write_file(self.workspace, "src/hello.txt", "hello")
        self.assertEqual(read_file(self.workspace, "src/hello.txt"), "hello")
        self.assertIn("hello.txt", list_files(self.workspace, "src"))

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ToolError):
            resolve_workspace_path(self.workspace, "../outside.txt")

    def test_registry_converts_tool_errors_to_text(self):
        result = ToolRegistry(self.workspace).execute("read_file", {"path": "missing.txt"})
        self.assertTrue(result.startswith("Tool error:"))

    def test_command_is_run_in_workspace(self):
        output = run_command(self.workspace, 'python -c "print(\'ok\')"')
        self.assertIn("Exit code: 0", output)
        self.assertIn("ok", output)

    def test_search_text_returns_file_and_line_number(self):
        write_file(self.workspace, "src/example.txt", "first\nneedle here\n")
        result = search_text(self.workspace, "needle")
        self.assertIn("src\\example.txt:2:", result)


if __name__ == "__main__":
    unittest.main()
