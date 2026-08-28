"""Read-only Git inspection helpers for agent review and verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tools.file_tools import ToolError


def _git(workspace: Path, *args: str, max_chars: int = 20_000) -> str:
    result = subprocess.run(["git", "-C", str(workspace), *args], text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    output = result.stdout or ""
    if result.returncode:
        raise ToolError(f"git {' '.join(args)} failed (exit {result.returncode}):\n{output[:max_chars]}")
    return output[:max_chars] + ("\n[truncated]" if len(output) > max_chars else "")


def git_status(workspace: Path) -> str:
    output = _git(workspace, "status", "--short")
    return output or "Working tree is clean."


def git_diff(workspace: Path) -> str:
    output = _git(workspace, "diff", "--stat")
    return output or "No unstaged changes."
