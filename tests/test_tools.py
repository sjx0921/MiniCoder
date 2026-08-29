import tempfile
import unittest
import os
from pathlib import Path

from tools.file_tools import ToolError, list_files, read_file, resolve_workspace_path, search_text, write_file
from tools.registry import ToolRegistry
from tools.shell_tool import run_command
from tools.shell_tool import classify_command


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

    def test_destructive_command_is_high_risk(self):
        risk, reason = classify_command("git reset --hard HEAD~1")
        self.assertEqual(risk, "high")
        self.assertIn("destructive", reason)

    def test_generated_directories_are_hidden_from_default_listing(self):
        (self.workspace / "__pycache__").mkdir()
        (self.workspace / ".venv").mkdir()
        write_file(self.workspace, "visible.txt", "ok")
        listing = list_files(self.workspace)
        self.assertIn("visible.txt", listing)
        self.assertNotIn("__pycache__", listing)
        self.assertNotIn(".venv", listing)

    def test_replace_rejects_ambiguous_text(self):
        write_file(self.workspace, "repeat.txt", "same same")
        from tools.file_tools import replace_in_file
        with self.assertRaises(ToolError):
            replace_in_file(self.workspace, "repeat.txt", "same", "new")

    def test_command_output_is_truncated(self):
        output = run_command(self.workspace, 'python -c "print(\'x\' * 30000)"')
        self.assertIn("[truncated after 20000 characters]", output)

    @unittest.skipUnless(os.name == "nt", "PowerShell timeout behavior is Windows-specific")
    def test_command_timeout_returns_clear_error(self):
        with self.assertRaises(ToolError) as context:
            run_command(self.workspace, "Start-Sleep -Seconds 2", timeout_seconds=1)
        self.assertIn("timed out after 1s", str(context.exception))

    @unittest.skipUnless(os.name == "nt", "PowerShell behavior is Windows-specific")
    def test_powershell_command_preserves_chinese_output(self):
        output = run_command(self.workspace, 'Write-Output "中文输出"')
        self.assertIn("中文输出", output)


if __name__ == "__main__":
    unittest.main()
