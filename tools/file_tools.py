"""Filesystem tools exposed to MiniCoder's language model."""

from __future__ import annotations

from pathlib import Path


class ToolError(RuntimeError):
    """An error that is safe to send back to the model."""


def resolve_workspace_path(workspace: Path, user_path: str) -> Path:
    """Resolve a path and ensure it remains inside the workspace."""
    root = workspace.resolve()
    candidate = Path(user_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ToolError(f"Path must be inside the workspace: {user_path}") from exc
    return resolved


def read_file(workspace: Path, path: str, max_chars: int = 20_000) -> str:
    target = resolve_workspace_path(workspace, path)
    if not target.is_file():
        raise ToolError(f"Not a readable file: {path}")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError(f"File is not valid UTF-8 text: {path}") from exc
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n[truncated after {max_chars} characters]"
    return content


def write_file(workspace: Path, path: str, content: str) -> str:
    target = resolve_workspace_path(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {target.relative_to(workspace.resolve())}"


def list_files(workspace: Path, path: str = ".", max_entries: int = 200) -> str:
    target = resolve_workspace_path(workspace, path)
    if not target.is_dir():
        raise ToolError(f"Not a directory: {path}")
    entries = sorted(target.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    lines = [("[dir] " if entry.is_dir() else "[file] ") + entry.name for entry in entries[:max_entries]]
    if len(entries) > max_entries:
        lines.append(f"[truncated: {len(entries) - max_entries} more entries]")
    return "\n".join(lines) or "[empty directory]"


def replace_in_file(workspace: Path, path: str, old_text: str, new_text: str) -> str:
    if not old_text:
        raise ToolError("old_text must not be empty")
    target = resolve_workspace_path(workspace, path)
    if not target.is_file():
        raise ToolError(f"Not a readable file: {path}")
    content = read_file(workspace, path, max_chars=10_000_000)
    occurrences = content.count(old_text)
    if occurrences != 1:
        raise ToolError(f"Expected old_text exactly once in {path}, found {occurrences} occurrences")
    target.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
    return f"Replaced text in {target.relative_to(workspace.resolve())}"


def search_text(workspace: Path, query: str, path: str = ".", max_results: int = 100) -> str:
    if not query:
        raise ToolError("query must not be empty")
    target = resolve_workspace_path(workspace, path)
    if not target.exists():
        raise ToolError(f"Path does not exist: {path}")
    files = [target] if target.is_file() else (entry for entry in target.rglob("*") if entry.is_file() and ".git" not in entry.parts)
    matches: list[str] = []
    for file_path in files:
        try:
            for line_number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
                if query in line:
                    matches.append(f"{file_path.relative_to(workspace.resolve())}:{line_number}: {line[:300]}")
                    if len(matches) >= max_results:
                        return "\n".join(matches) + "\n[truncated]"
        except (UnicodeDecodeError, OSError):
            continue
    return "\n".join(matches) or "No matches found."
