"""The MiniCoder tool-calling control loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from llm import LLMClient, LLMError
from prompts import build_system_prompt
from runtime import describe_environment
from tools.registry import TOOL_DEFINITIONS, ToolRegistry
from tools.git_tools import git_diff, git_status


class CodingAgent:
    def __init__(self, workspace: Path, client: LLMClient, max_turns: int = 20, max_history_chars: int = 80_000, approval_callback: Callable[[str, dict[str, Any], str, str], bool] | None = None) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        if max_history_chars < 1_000:
            raise ValueError("max_history_chars must be at least 1000")
        self.workspace = workspace.resolve()
        self.client = client
        self.max_turns = max_turns
        self.max_history_chars = max_history_chars
        self.registry = ToolRegistry(self.workspace)
        self.system_prompt = build_system_prompt(describe_environment(self.workspace))
        self.approval_callback = approval_callback or (lambda _name, _arguments, _risk, _reason: True)
        self.messages: list[dict[str, Any]] = []
        self.plan: list[dict[str, str]] = []
        self.task_log: list[str] = []
        self.activity_log: list[str] = []
        self._awaiting_initial_plan = False
        self.reset()

    def reset(self) -> None:
        """Clear conversation state while preserving the configured workspace."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.plan = []
        self.task_log = []
        self.activity_log = []
        self._awaiting_initial_plan = False

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
        plan_text = "; ".join(f"[{item['status']}] {item['step']}" for item in self.plan) or "No plan recorded."
        activities = " | ".join(self.activity_log[-12:]) or "No tool activity recorded."
        summary = {
            "role": "system",
            "content": f"Structured local session summary: tasks={self.task_log[-5:]}; plan={plan_text}; recent tool activity={activities}. {omitted} earlier messages were compacted. Inspect workspace files and recent messages before acting.",
        }
        self.messages = [system, summary, *reversed(recent)]

    def run(self, task: str) -> str:
        if not task.strip():
            return "Please provide a task."
        self._awaiting_initial_plan = self._requires_initial_plan(task)
        self.task_log.append(task)
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
                if self._awaiting_initial_plan:
                    self.messages.append({"role": "user", "content": "你尚未遵守要求：此任务明确要求先制定计划。请先且仅先调用 update_plan，然后再继续。"})
                    continue
                final_message = str(assistant_message.get("content") or "Agent finished without a final message.")
                return f"{final_message}\n\nLocal Git review:\n{self._git_review()}"
            if self._awaiting_initial_plan and tool_calls[0].get("function", {}).get("name") != "update_plan":
                for call in tool_calls:
                    name = call.get("function", {}).get("name", "")
                    result = "Tool error: this task explicitly requires planning first. The first tool call must be update_plan; no tool was executed."
                    print(f"[进度 第{turn}轮] 已阻止 {name}：必须先制定计划")
                    self.activity_log.append(f"{name}: blocked until update_plan")
                    self.messages.append({"role": "tool", "tool_call_id": call.get("id", "missing-id"), "content": result})
                continue
            for call in tool_calls:
                function = call.get("function", {})
                name = function.get("name", "")
                arguments: dict[str, Any] = {}
                try:
                    arguments = json.loads(function.get("arguments", "{}"))
                except json.JSONDecodeError as exc:
                    result = f"Tool error: invalid JSON arguments: {exc}"
                else:
                    if name == "update_plan":
                        result = self._update_plan(arguments)
                        if not result.startswith("Tool error:"):
                            self._awaiting_initial_plan = False
                    else:
                        risk, reason = self.registry.risk_level(name, arguments)
                        if self.registry.requires_confirmation(name) and not self.approval_callback(name, arguments, risk, reason):
                            result = f"Tool denied by user: {name} was not executed."
                        else:
                            result = self.registry.execute(name, arguments)
                print(f"[进度 第{turn}轮] {self._progress_message(name, arguments)}")
                print(f"[工具结果] {result[:500]}")
                self.activity_log.append(f"{name}: {result[:300]}")
                self.messages.append({"role": "tool", "tool_call_id": call.get("id", "missing-id"), "content": result})
        return f"Agent stopped after reaching the maximum of {self.max_turns} turns."

    @staticmethod
    def _requires_initial_plan(task: str) -> bool:
        normalized = task.lower()
        phrases = ("先制定计划", "先制订计划", "先给出计划", "先做计划", "first make a plan", "plan first")
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _progress_message(name: str, arguments: dict[str, Any]) -> str:
        labels = {
            "inspect_environment": "正在确认运行环境和推荐测试方式",
            "update_plan": "正在更新任务计划",
            "list_files": "正在查看项目目录",
            "read_file": "正在读取文件",
            "search_text": "正在搜索项目文本",
            "write_file": "正在写入实现文件",
            "replace_in_file": "正在做精确代码替换",
            "run_command": "正在执行验证命令",
            "git_status": "正在检查 Git 工作区状态",
            "git_diff": "正在审查文件改动",
        }
        detail = arguments.get("path") or arguments.get("command") or ""
        return f"{labels.get(name, '正在调用本地工具')}{(': ' + str(detail)) if detail else ''}"

    def _update_plan(self, arguments: dict[str, Any]) -> str:
        steps = arguments.get("steps")
        if not isinstance(steps, list) or not steps:
            return "Tool error: steps must be a non-empty list"
        validated: list[dict[str, str]] = []
        for item in steps:
            if not isinstance(item, dict) or not isinstance(item.get("step"), str) or item.get("status") not in {"pending", "in_progress", "completed"}:
                return "Tool error: each plan item needs a string step and valid status"
            validated.append({"step": item["step"], "status": item["status"]})
        if sum(item["status"] == "in_progress" for item in validated) > 1:
            return "Tool error: only one plan step may be in_progress"
        self.plan = validated
        return "Plan updated: " + "; ".join(f"[{item['status']}] {item['step']}" for item in self.plan)

    def _git_review(self) -> str:
        try:
            return f"Status:\n{git_status(self.workspace)}\nDiff stat:\n{git_diff(self.workspace)}"
        except Exception as exc:  # A workspace need not be a Git repository.
            return f"Unavailable: {exc}"
