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
    if not output:
        return "Git 工作区干净：没有已暂存、未暂存或未跟踪文件。"
    staged = [line for line in output.splitlines() if len(line) >= 2 and line[0] not in {" ", "?"}]
    unstaged = [line for line in output.splitlines() if len(line) >= 2 and line[1] not in {" ", "?"}]
    untracked = [line for line in output.splitlines() if line.startswith("??")]
    return "\n".join((
        "Git 工作区不干净：",
        f"- 已暂存条目：{len(staged)}",
        f"- 未暂存条目：{len(unstaged)}",
        f"- 未跟踪条目：{len(untracked)}",
        "原始状态：",
        output,
    ))


def git_diff(workspace: Path) -> str:
    unstaged = _git(workspace, "diff", "--stat")
    staged = _git(workspace, "diff", "--cached", "--stat")
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard")
    parts = []
    if unstaged:
        parts.append("未暂存差异：\n" + unstaged)
    if staged:
        parts.append("已暂存差异：\n" + staged)
    if untracked:
        parts.append("未跟踪文件（普通 git diff 不会显示其内容）：\n" + untracked)
    return "\n".join(parts) or "Git 没有已暂存、未暂存或未跟踪改动。"
