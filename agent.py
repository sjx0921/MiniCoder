"""The MiniCoder tool-calling control loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import LLMClient, LLMError
from prompts import SYSTEM_PROMPT
from tools.registry import TOOL_DEFINITIONS, ToolRegistry


class CodingAgent:
    def __init__(self, workspace: Path, client: LLMClient, max_turns: int = 20, max_history_chars: int = 80_000) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        if max_history_chars < 1_000:
            raise ValueError("max_history_chars must be at least 1000")
        self.workspace = workspace.resolve()
        self.client = client
        self.max_turns = max_turns
        self.max_history_chars = max_history_chars
        self.registry = ToolRegistry(self.workspace)
        self.messages: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        """Clear conversation state while preserving the configured workspace."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _history_size(self) -> int:
        return sum(len(str(message.get("content") or "")) + len(str(message.get("tool_calls") or "")) for message in self.messages)

    def _compact_history(self) -> None:
        """Bound API payload size while retaining recent conversational state.

        Tool calls and their outputs occur in linked assistant/tool messages, so
        they are retained as complete recent messages rather than cut apart.
        """
        if self._history_size() <= self.max_history_chars:
            return
        system = self.messages[0]
        recent: list[dict[str, Any]] = []
        size = 0
        for message in reversed(self.messages[1:]):
            message_size = len(str(message.get("content") or "")) + len(str(message.get("tool_calls") or ""))
            if recent and size + message_size > self.max_history_chars // 2:
                break
            recent.append(message)
            size += message_size
        omitted = len(self.messages) - 1 - len(recent)
        summary = {
            "role": "system",
            "content": f"Conversation history was compacted locally. {omitted} earlier messages were omitted; inspect workspace files and recent messages before acting.",
        }
        self.messages = [system, summary, *reversed(recent)]

    def run(self, task: str) -> str:
        if not task.strip():
            return "Please provide a task."
        self.messages.append({"role": "user", "content": task})
        for turn in range(1, self.max_turns + 1):
            self._compact_history()
            try:
                assistant_message = self.client.complete(self.messages, TOOL_DEFINITIONS)
            except LLMError as exc:
                return f"Agent stopped: {exc}"
            self.messages.append(assistant_message)
            tool_calls = assistant_message.get("tool_calls") or []
            if not tool_calls:
                return str(assistant_message.get("content") or "Agent finished without a final message.")
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name", "")
                try:
                    arguments = json.loads(function.get("arguments", "{}"))
                except json.JSONDecodeError as exc:
                    result = f"Tool error: invalid JSON arguments: {exc}"
                else:
                    result = self.registry.execute(name, arguments)
                print(f"[turn {turn}] {name}: {result[:500]}")
                self.messages.append({"role": "tool", "tool_call_id": call.get("id", "missing-id"), "content": result})
        return f"Agent stopped after reaching the maximum of {self.max_turns} turns."
