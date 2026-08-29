"""Runtime inspection used to ground the agent in its actual environment."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def describe_environment(workspace: Path) -> str:
    workspace = workspace.resolve()
    if os.name == "nt":
        shell = "Windows PowerShell"
        command_hint = "Use PowerShell syntax when calling run_command. Prefer local file tools over shell commands."
    else:
        shell = os.getenv("SHELL", "/bin/sh")
        command_hint = "Use POSIX shell syntax when calling run_command. Prefer local file tools over shell commands."

    has_pytest_config = any((workspace / name).exists() for name in ("pytest.ini", "tox.ini"))
    has_unittest = any(workspace.glob("tests/test_*.py"))
    if has_pytest_config:
        test_hint = "pytest configuration detected; inspect it before selecting the test command."
    elif has_unittest:
        test_hint = "unittest-style tests detected; preferred first command: python -m unittest discover -s tests -v"
    else:
        test_hint = "No test runner was inferred; inspect project files before running tests."

    return "\n".join((
        "Runtime environment (authoritative):",
        f"- Operating system: {platform.system()} {platform.release()}",
        f"- Shell used by run_command: {shell}",
        f"- Workspace absolute path: {workspace}",
        f"- Python: {sys.version.split()[0]}",
        f"- Test guidance: {test_hint}",
        f"- Command guidance: {command_hint}",
    ))
