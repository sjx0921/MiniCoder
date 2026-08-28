"""The MiniCoder tool-calling control loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import LLMClient, LLMError
from prompts import SYSTEM_PROMPT
from tools.registry import TOOL_DEFINITIONS, ToolRegistry


class CodingAgent:
    def __init__(self, workspace: Path, client: LLMClient, max_turns: int = 20) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        self.workspace = workspace.resolve()
        self.client = client
        self.max_turns = max_turns
        self.registry = ToolRegistry(self.workspace)

    def run(self, task: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        for turn in range(1, self.max_turns + 1):
            try:
                assistant_message = self.client.complete(messages, TOOL_DEFINITIONS)
            except LLMError as exc:
                return f"Agent stopped: {exc}"
            messages.append(assistant_message)
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
                messages.append({"role": "tool", "tool_call_id": call.get("id", "missing-id"), "content": result})
        return f"Agent stopped after reaching the maximum of {self.max_turns} turns."
