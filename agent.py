"""The MiniCoder tool-calling control loop."""

from __future__ import annotations

import json
import re
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
        self._tools_forbidden = False
        self._no_test_changes = False
        self._allowed_write_paths: set[str] = set()
        self._denied_operations: set[str] = set()
        self._denied_write_paths: set[str] = set()
        self._mutation_version = 0
        self._last_verified_mutation_version = -1
        self._successful_commands: dict[str, int] = {}
        self._session_mutations: set[str] = set()
        self.reset()

    def reset(self) -> None:
        """Clear conversation state while preserving the configured workspace."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.plan = []
        self.task_log = []
        self.activity_log = []
        self._awaiting_initial_plan = False
        self._tools_forbidden = False
        self._no_test_changes = False
        self._allowed_write_paths = set()
        self._denied_operations = set()
        self._denied_write_paths = set()
        self._mutation_version = 0
        self._last_verified_mutation_version = -1
        self._successful_commands = {}
        self._session_mutations = set()

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
            "content": f"Structured local session summary: tasks={self.task_log[-5:]}; plan={plan_text}; constraints=no_tools:{self._tools_forbidden}, no_test_changes:{self._no_test_changes}, allowed_paths:{sorted(self._allowed_write_paths)}; denied_operations:{sorted(self._denied_operations)}; mutation_version:{self._mutation_version}; last_verified_version:{self._last_verified_mutation_version}; recent tool activity={activities}. {omitted} earlier messages were compacted. Inspect workspace files and recent messages before acting.",
        }
        self.messages = [system, summary, *reversed(recent)]

    def run(self, task: str) -> str:
        if not task.strip():
            return "Please provide a task."
        self._begin_task(task)
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
                if self._needs_reverification():
                    self.messages.append({"role": "user", "content": "最后一次成功测试后又发生了文件修改。不得宣布验证成功；请先运行相关验证命令并检查结果。"})
                    continue
                final_message = str(assistant_message.get("content") or "Agent finished without a final message.")
                return self._final_response(final_message)
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
                        result = self._execute_with_policy(name, arguments)
                print(f"[进度 第{turn}轮] {self._progress_message(name, arguments)}")
                print(f"[工具结果] {result[:500]}")
                self.activity_log.append(f"{name}: {result[:300]}")
                self.messages.append({"role": "tool", "tool_call_id": call.get("id", "missing-id"), "content": result})
        return f"Agent stopped after reaching the maximum of {self.max_turns} turns; task may be incomplete."

    def _begin_task(self, task: str) -> None:
        # Conversation messages persist, while all execution state below belongs
        # only to the newly submitted task.
        self.plan = []
        self.activity_log = []
        self._awaiting_initial_plan = self._requires_initial_plan(task)
        self._tools_forbidden = any(phrase in task.lower() for phrase in ("不要执行任何工具", "不要使用任何工具", "do not use any tools", "don't use tools"))
        self._no_test_changes = self._detect_no_test_modifications(task)
        self._allowed_write_paths = set(re.findall(r"(?:只改|仅改|only modify)\s*[`'\"]?([\w./\\-]+)", task, flags=re.IGNORECASE))
        self._denied_operations = set()
        self._denied_write_paths = set()
        self._mutation_version = 0
        self._last_verified_mutation_version = -1
        self._successful_commands = {}
        self._session_mutations = set()
        language = "Chinese" if re.search(r"[\u3400-\u9fff]", task) else "English"
        self.system_prompt = build_system_prompt(describe_environment(self.workspace), language)
        self.messages[0] = {"role": "system", "content": self.system_prompt}

    @staticmethod
    def _detect_no_test_modifications(task: str) -> bool:
        """Recognize common Chinese/English ways to make tests read-only."""
        text = task.lower()
        patterns = (
            r"(?:不要|禁止|不许|别|不可|不得).{0,12}(?:修改|改动|改|动|写入|编辑).{0,20}(?:测试|tests?)",
            r"(?:测试|tests?).{0,20}(?:不要|禁止|不许|不可|不得).{0,12}(?:修改|改动|改|动|写入|编辑)",
            r"(?:测试|tests?).{0,16}(?:目录|文件|下|folder|directory).{0,12}(?:禁止|不可|不得|不要|不许).{0,12}(?:修改|改动|改|动|写入|编辑)",
            r"(?:do not|don't|never).{0,20}(?:modify|edit|write).{0,20}(?:test|tests)",
        )
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _operation_signature(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "run_command":
            return f"command:{' '.join(str(arguments.get('command', '')).lower().split())}"
        if name in {"write_file", "replace_in_file"}:
            return f"write:{str(arguments.get('path', '')).replace('\\', '/').lower()}"
        return f"{name}:{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"

    def _execute_with_policy(self, name: str, arguments: dict[str, Any]) -> str:
        signature = self._operation_signature(name, arguments)
        if self._tools_forbidden:
            return "工具已被用户禁止：本任务要求不要执行任何工具。"
        if signature in self._denied_operations and not self._explicit_retry_requested():
            return "该操作此前已被用户拒绝；未收到明确重试要求，因此不会再次请求或执行。"
        if name == "run_command" and any(path and path.lower() in str(arguments.get("command", "")).lower() for path in self._denied_write_paths):
            return "该命令可能绕过此前被拒绝的文件修改；未执行。"
        if name in {"write_file", "replace_in_file"}:
            path = str(arguments.get("path", "")).replace("\\", "/")
            path_parts = tuple(part.lower() for part in Path(path).parts)
            if self._no_test_changes and ("tests" in path_parts or Path(path).name.lower().startswith("test_")):
                return "任务约束禁止修改测试文件；未执行。"
            if self._allowed_write_paths and path not in self._allowed_write_paths:
                return f"任务约束只允许修改 {sorted(self._allowed_write_paths)}；未执行 {path}。"
        if name == "run_command" and self._successful_commands.get(signature) == self._mutation_version:
            return "该命令已在当前代码版本成功执行；为避免重复，未再次运行。"
        risk, reason = self.registry.risk_level(name, arguments)
        if self.registry.requires_confirmation(name) and not self.approval_callback(name, arguments, risk, reason):
            self._denied_operations.add(signature)
            if name in {"write_file", "replace_in_file"}:
                self._denied_write_paths.add(str(arguments.get("path", "")).replace("\\", "/"))
            return f"用户已拒绝此操作：{name} 未执行。这不是普通工具错误，不应自动重试或绕过。"
        result = self.registry.execute(name, arguments)
        if name in {"write_file", "replace_in_file"} and not result.startswith("Tool error:"):
            self._mutation_version += 1
            self._session_mutations.add(str(arguments.get("path", "")))
        if name == "run_command" and result.startswith("Exit code: 0"):
            self._successful_commands[signature] = self._mutation_version
            if self._is_test_command(str(arguments.get("command", ""))):
                self._last_verified_mutation_version = self._mutation_version
        return result

    def _explicit_retry_requested(self) -> bool:
        return bool(self.task_log and any(token in self.task_log[-1].lower() for token in ("重试", "再次尝试", "retry", "try again")))

    @staticmethod
    def _is_test_command(command: str) -> bool:
        normalized = command.lower()
        return any(token in normalized for token in ("unittest", "pytest", "npm test", "cargo test", "go test"))

    def _needs_reverification(self) -> bool:
        return self._last_verified_mutation_version >= 0 and self._mutation_version > self._last_verified_mutation_version and not self._tools_forbidden

    def _final_response(self, final_message: str) -> str:
        plan_state = "; ".join(f"[{item['status']}] {item['step']}" for item in self.plan) or "未创建计划"
        facts = [
            "框架执行事实：",
            f"- 本任务会话内修改的文件：{', '.join(sorted(self._session_mutations)) or '无'}",
            f"- 最近成功测试对应代码版本：{self._last_verified_mutation_version if self._last_verified_mutation_version >= 0 else '未记录'}",
            f"- 当前代码修改版本：{self._mutation_version}",
            f"- 当前计划：{plan_state}",
        ]
        if self._tools_forbidden:
            facts.append("- 用户明确禁止工具：框架未执行自动 Git 审查。")
            return final_message + "\n\n" + "\n".join(facts)
        if self._session_mutations or "git" in self.task_log[-1].lower():
            facts.append("- 自动 Git 审查（框架操作，不是模型主动工具调用）：\n" + self._git_review())
        return final_message + "\n\n" + "\n".join(facts)

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
            "run_command": "正在执行命令",
            "git_status": "正在检查 Git 工作区状态",
            "git_diff": "正在审查文件改动",
        }
        if name == "run_command" and CodingAgent._is_test_command(str(arguments.get("command", ""))):
            labels[name] = "正在运行测试"
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
        if validated == self.plan:
            return "Plan unchanged: no phase transition occurred."
        self.plan = validated
        return "Plan updated: " + "; ".join(f"[{item['status']}] {item['step']}" for item in self.plan)

    def _git_review(self) -> str:
        try:
            return f"Git 状态：\n{git_status(self.workspace)}\nGit 改动审查：\n{git_diff(self.workspace)}"
        except Exception as exc:  # A workspace need not be a Git repository.
            return f"Unavailable: {exc}"
