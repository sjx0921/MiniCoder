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
            self.assertTrue(result.startswith("Completed."))
            self.assertEqual((workspace / "answer.txt").read_text(encoding="utf-8"), "done")
            self.assertEqual(client.calls[1][-1]["role"], "tool")

    def test_loop_stops_at_turn_limit(self):
        repeated_call = {"role": "assistant", "tool_calls": [{"id": "call_1", "function": {"name": "list_files", "arguments": "{}"}}]}
        client = FakeClient([repeated_call, repeated_call])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client, max_turns=2).run("loop")
        self.assertIn("maximum of 2 turns", result)

    def test_history_persists_between_tasks_and_can_be_reset(self):
        client = FakeClient([
            {"role": "assistant", "content": "First answer."},
            {"role": "assistant", "content": "Second answer."},
            {"role": "assistant", "content": "Fresh answer."},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            agent.run("First task")
            agent.run("Follow up")
            second_request = client.calls[1]
            self.assertTrue(any(message.get("content") == "First task" for message in second_request))
            self.assertTrue(any(message.get("content") == "First answer." for message in second_request))
            agent.reset()
            agent.run("New task")
            third_request = client.calls[2]
            self.assertEqual([message["role"] for message in third_request], ["system", "user"])

    def test_history_is_compacted_before_a_new_model_request(self):
        client = FakeClient([
            {"role": "assistant", "content": "x" * 900},
            {"role": "assistant", "content": "done"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client, max_history_chars=1_000)
            agent.run("first task")
            agent.run("second task")
        second_request = client.calls[1]
        self.assertTrue(any("Structured local session summary" in message.get("content", "") for message in second_request))

    def test_mutating_tool_can_be_denied(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "call_1", "function": {"name": "write_file", "arguments": '{"path":"blocked.txt","content":"no"}'}}]},
            {"role": "assistant", "content": "Acknowledged."},
        ])
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = CodingAgent(workspace, client, approval_callback=lambda _name, _args, _risk, _reason: False).run("try writing")
            self.assertTrue(result.startswith("Acknowledged."))
            self.assertFalse((workspace / "blocked.txt").exists())
            self.assertIn("denied by user", client.calls[1][-1]["content"])

    def test_plan_is_stored_and_returned_to_model(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "plan_1", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Inspect files","status":"in_progress"},{"step":"Implement","status":"pending"}]}'}}]},
            {"role": "assistant", "content": "Plan created."},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            agent.run("make a plan")
        self.assertEqual(agent.plan[0], {"step": "Inspect files", "status": "in_progress"})
        self.assertIn("Plan updated", client.calls[1][-1]["content"])


if __name__ == "__main__":
    unittest.main()
