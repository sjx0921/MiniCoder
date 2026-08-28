"""Tool schemas and dispatcher used by the agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tools import ToolError, list_files, read_file, replace_in_file, run_command, write_file


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": "list_files", "description": "List a directory inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory relative to workspace; defaults to ."}}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or fully overwrite a UTF-8 text file inside the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "replace_in_file", "description": "Replace an exact unique string in a text file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command from the workspace. Inspect output and fix failures.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300}}, "required": ["command"]}}},
]


class ToolRegistry:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self._tools: dict[str, Callable[..., str]] = {
            "list_files": list_files,
            "read_file": read_file,
            "write_file": write_file,
            "replace_in_file": replace_in_file,
            "run_command": run_command,
        }

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

