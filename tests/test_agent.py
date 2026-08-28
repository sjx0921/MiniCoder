import tempfile
import unittest
from pathlib import Path

from agent import CodingAgent


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append(list(messages))
        return next(self.responses)


class AgentLoopTests(unittest.TestCase):
    def test_tool_call_is_executed_and_returned_to_model(self):
        client = FakeClient([
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "write_file", "arguments": '{"path":"answer.txt","content":"done"}'}}]},
            {"role": "assistant", "content": "Completed."},
        ])
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = CodingAgent(workspace, client, max_turns=3).run("create a file")
            self.assertEqual(result, "Completed.")
            self.assertEqual((workspace / "answer.txt").read_text(encoding="utf-8"), "done")
            self.assertEqual(client.calls[1][-1]["role"], "tool")

    def test_loop_stops_at_turn_limit(self):
        repeated_call = {"role": "assistant", "tool_calls": [{"id": "call_1", "function": {"name": "list_files", "arguments": "{}"}}]}
        client = FakeClient([repeated_call, repeated_call])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client, max_turns=2).run("loop")
        self.assertIn("maximum of 2 turns", result)


if __name__ == "__main__":
    unittest.main()
