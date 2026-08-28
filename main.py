"""Command-line entry point for MiniCoder."""

from __future__ import annotations

import argparse
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
    return parser


def run_task(task: str, args: argparse.Namespace) -> None:
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace is not a directory: {workspace}")
    client = LLMClient(base_url=args.base_url, model=args.model)
    agent = CodingAgent(workspace, client, max_turns=args.max_turns)
    print(f"MiniCoder workspace: {workspace}")
    print(agent.run(task))


def main() -> None:
    load_dotenv(Path(".env"))
    args = build_parser().parse_args()
    if args.task:
        run_task(args.task, args)
        return
    print("MiniCoder interactive mode. Type 'exit' or 'quit' to leave.")
    while True:
        try:
            task = input("\nTask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if task.lower() in {"exit", "quit"}:
            return
        if task:
            run_task(task, args)


if __name__ == "__main__":
    main()
