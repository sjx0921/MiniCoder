"""Command-line entry point for MiniCoder."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent import CodingAgent
from config import load_dotenv
from llm import LLMClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A lightweight local coding agent.")
    parser.add_argument("task", nargs="?", help="Programming task to complete. Omit for interactive mode.")
    parser.add_argument("--workspace", default=".", help="Directory the agent may access (default: current directory).")
    parser.add_argument("--model", help="OpenAI-compatible model name; overrides MINICODER_MODEL.")
    parser.add_argument("--base-url", help="OpenAI-compatible API base URL; overrides MINICODER_BASE_URL.")
    parser.add_argument("--max-turns", type=int, default=20, help="Maximum model/tool rounds (default: 20).")
    parser.add_argument("--max-history-chars", type=int, default=80_000, help="Maximum approximate conversation size before compaction.")
    parser.add_argument("--approval-mode", choices=("auto", "ask", "strict"), default="ask", help="auto: approve low/medium risk; ask: approve only low risk; strict: ask before every mutation.")
    parser.add_argument("--auto-approve", action="store_true", help="Deprecated alias for --approval-mode auto.")
    return parser


def create_agent(args: argparse.Namespace) -> CodingAgent:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace is not a directory: {workspace}")
    client = LLMClient(base_url=args.base_url, model=args.model)
    if args.auto_approve and args.approval_mode != "ask":
        raise SystemExit("--auto-approve 不能与显式 --approval-mode 同时使用")
    approval_mode = "auto" if args.auto_approve else args.approval_mode
    def approve(name: str, arguments: dict, risk: str, reason: str) -> bool:
        auto_allowed = (approval_mode == "auto" and risk in {"low", "medium"}) or (approval_mode == "ask" and risk == "low")
        if auto_allowed:
            return True
        print(f"\n需要确认（{risk} 风险：{reason}）— {name}: {json.dumps(arguments, ensure_ascii=False)}")
        return input("允许执行？[y/N] ").strip().lower() in {"y", "yes"}

    return CodingAgent(workspace, client, max_turns=args.max_turns, max_history_chars=args.max_history_chars, approval_callback=approve)


def run_task(task: str, agent: CodingAgent) -> None:
    print(agent.run(task))


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv(Path(".env"))
    args = build_parser().parse_args()
    agent = create_agent(args)
    if args.task:
        print(f"MiniCoder 工作区：{agent.workspace}")
        run_task(args.task, agent)
        return
    print(f"MiniCoder 工作区：{agent.workspace}")
    print("交互模式：输入 exit 或 quit 退出；输入 /reset 清空会话历史。")
    while True:
        try:
            task = input("\n任务> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if task.lower() in {"exit", "quit"}:
            return
        if task == "/reset":
            agent.reset()
            print("会话历史已清空。")
            continue
        if task:
            run_task(task, agent)


if __name__ == "__main__":
    main()
