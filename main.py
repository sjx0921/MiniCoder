"""Command-line entry point for MiniCoder."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--auto-approve", action="store_true", help="Run file-changing tools and commands without asking for approval.")
    return parser


def create_agent(args: argparse.Namespace) -> CodingAgent:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace is not a directory: {workspace}")
    client = LLMClient(base_url=args.base_url, model=args.model)
    def approve(name: str, arguments: dict) -> bool:
        if args.auto_approve:
            return True
        print(f"\nApproval required for {name}: {json.dumps(arguments, ensure_ascii=False)}")
        return input("Allow? [y/N] ").strip().lower() in {"y", "yes"}

    return CodingAgent(workspace, client, max_turns=args.max_turns, max_history_chars=args.max_history_chars, approval_callback=approve)


def run_task(task: str, agent: CodingAgent) -> None:
    print(agent.run(task))


def main() -> None:
    load_dotenv(Path(".env"))
    args = build_parser().parse_args()
    agent = create_agent(args)
    if args.task:
        print(f"MiniCoder workspace: {agent.workspace}")
        run_task(args.task, agent)
        return
    print(f"MiniCoder workspace: {agent.workspace}")
    print("Interactive mode. Type 'exit' or 'quit' to leave; type '/reset' to clear chat history.")
    while True:
        try:
            task = input("\nTask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if task.lower() in {"exit", "quit"}:
            return
        if task == "/reset":
            agent.reset()
            print("Conversation history cleared.")
            continue
        if task:
            run_task(task, agent)


if __name__ == "__main__":
    main()
