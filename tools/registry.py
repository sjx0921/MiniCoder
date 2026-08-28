"""Tool schemas and dispatcher used by the agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tools import ToolError, git_diff, git_status, list_files, read_file, replace_in_file, run_command, search_text, write_file


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "list_files", "description": "List a directory inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory relative to workspace; defaults to ."}}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "search_text", "description": "Search UTF-8 workspace files for exact text and return matching lines.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or fully overwrite a UTF-8 text file inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "replace_in_file", "description": "Replace an exact unique string in a text file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command from the workspace. Inspect output and fix failures.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "git_status", "description": "Show the current Git working tree status. Read-only.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "git_diff", "description": "Show a compact stat of unstaged Git changes. Read-only.", "parameters": {"type": "object", "properties": {}, "required": []}}},
]


class ToolRegistry:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self._tools: dict[str, Callable[..., str]] = {
            "list_files": list_files,
            "read_file": read_file,
            "write_file": write_file,
            "replace_in_file": replace_in_file,
            "search_text": search_text,
            "run_command": run_command,
            "git_status": git_status,
            "git_diff": git_diff,
        }

    @staticmethod
    def requires_confirmation(name: str) -> bool:
        """Writes and shell commands require an explicit human approval in CLI mode."""
        return name in {"write_file", "replace_in_file", "run_command"}

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Tool error: unknown tool '{name}'"
        if not isinstance(arguments, dict):
            return "Tool error: arguments must be a JSON object"
        try:
            return tool(self.workspace, **arguments)
        except TypeError as exc:
            return f"Tool error: invalid arguments for {name}: {exc}"
        except ToolError as exc:
            return f"Tool error: {exc}"
