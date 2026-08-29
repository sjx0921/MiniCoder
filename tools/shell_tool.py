"""Local command execution with a workspace cwd and bounded output."""

from __future__ import annotations

import re
import os
import shutil
import subprocess
from pathlib import Path

from tools.file_tools import ToolError


def classify_command(command: str) -> tuple[str, str]:
    """Classify shell commands for human approval; this is not an OS sandbox."""
    normalized = command.lower()
    high_risk_patterns = {
        r"\brm\s+.*-[a-z]*r": "recursive deletion",
        r"\bdel\s+": "file deletion",
        r"\bremove-item\b": "file deletion",
        r"\bformat\b": "disk formatting",
        r"\bshutdown\b|\brestart-computer\b": "system shutdown",
        r"\bgit\s+reset\s+--hard\b": "destructive Git reset",
        r"\bgit\s+clean\s+-[a-z]*f": "destructive Git clean",
    }
    for pattern, reason in high_risk_patterns.items():
        if re.search(pattern, normalized):
            return "high", reason
    if re.search(r"\b(curl|wget|invoke-webrequest|npm\s+install|pip\s+install)\b", normalized):
        return "medium", "network or dependency operation"
    return "low", "local command"


def run_command(workspace: Path, command: str, timeout_seconds: int = 60, max_chars: int = 20_000) -> str:
    if not command.strip():
        raise ToolError("command must not be empty")
    if not 1 <= timeout_seconds <= 300:
        raise ToolError("timeout_seconds must be between 1 and 300")
    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not powershell:
            raise ToolError("Windows PowerShell was not found; cannot execute a command safely")
        utf8_prefix = "$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        invocation: list[str] = [powershell, "-NoProfile", "-NonInteractive", "-Command", utf8_prefix + command]
    else:
        invocation = ["/bin/sh", "-lc", command]
    try:
        result = subprocess.run(
            invocation, cwd=workspace, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        raise ToolError(f"Command timed out after {timeout_seconds}s. Output:\n{output[:max_chars]}") from exc
    output = result.stdout or ""
    if len(output) > max_chars:
        output = output[:max_chars] + f"\n[truncated after {max_chars} characters]"
    return f"Exit code: {result.returncode}\n{output}"
