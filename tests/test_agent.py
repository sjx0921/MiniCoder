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
            self.assertIn("用户已拒绝", client.calls[1][-1]["content"])

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

    def test_system_prompt_includes_runtime_context(self):
        client = FakeClient([{"role": "assistant", "content": "done"}])
        with tempfile.TemporaryDirectory() as directory:
            CodingAgent(Path(directory), client).run("check")
        self.assertIn("Runtime environment (authoritative)", client.calls[0][0]["content"])

    def test_explicit_plan_first_blocks_other_first_tool_call(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "blocked_1", "function": {"name": "list_files", "arguments": "{}"}}]},
            {"role": "assistant", "tool_calls": [{"id": "plan_1", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Inspect","status":"in_progress"}]}'}}]},
            {"role": "assistant", "content": "Finished."},
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client).run("先制定计划，然后检查项目")
        self.assertTrue(result.startswith("Finished."))
        self.assertIn("first permitted tool call is update_plan", client.calls[1][-1]["content"])
        self.assertEqual(client.calls[2][-1]["content"].split(":")[0], "Plan updated")

    def test_plan_first_allows_update_plan_as_first_tool_call(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "plan", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Inspect","status":"in_progress"}]}'}}]},
            {"role": "assistant", "content": "planned"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            result = agent.run("先制定计划，然后继续")
        self.assertTrue(result.startswith("planned"))
        self.assertEqual(agent.plan, [{"step": "Inspect", "status": "in_progress"}])
        self.assertIn("Plan updated", client.calls[1][-1]["content"])

    def test_plan_first_batch_executes_plan_and_blocks_other_tools(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [
                {"id": "environment", "function": {"name": "inspect_environment", "arguments": "{}"}},
                {"id": "plan", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Inspect","status":"in_progress"}]}'}} ,
                {"id": "files", "function": {"name": "list_files", "arguments": "{}"}},
            ]},
            {"role": "assistant", "content": "planned"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            result = agent.run("先制定计划，再检查项目")
        self.assertTrue(result.startswith("planned"))
        tool_results = [message["content"] for message in client.calls[1] if message["role"] == "tool"]
        self.assertEqual(sum("Plan updated" in content for content in tool_results), 1)
        self.assertEqual(sum("first permitted tool call" in content for content in tool_results), 2)
        self.assertEqual(agent.plan, [{"step": "Inspect", "status": "in_progress"}])

    def test_plan_first_allows_normal_tool_on_next_model_turn(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "plan", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Inspect","status":"in_progress"}]}'}}]},
            {"role": "assistant", "tool_calls": [{"id": "files", "function": {"name": "list_files", "arguments": "{}"}}]},
            {"role": "assistant", "content": "done"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client).run("先制定计划，然后检查目录")
        self.assertTrue(result.startswith("done"))
        self.assertIn("[empty directory]", client.calls[2][-1]["content"])

    def test_denied_operation_is_not_requested_twice(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "one", "function": {"name": "write_file", "arguments": '{"path":"x.txt","content":"x"}'}}]},
            {"role": "assistant", "tool_calls": [{"id": "two", "function": {"name": "write_file", "arguments": '{"path":"x.txt","content":"x"}'}}]},
            {"role": "assistant", "content": "stopped"},
        ])
        approvals = []
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client, approval_callback=lambda *args: approvals.append(args) or False).run("write a file")
        self.assertTrue(result.startswith("stopped"))
        self.assertEqual(len(approvals), 1)
        self.assertIn("此前已被用户拒绝", client.calls[2][-1]["content"])

    def test_mutation_after_successful_test_forces_reverification(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "test1", "function": {"name": "run_command", "arguments": '{"command":"python -m unittest discover -s tests -v"}'}}]},
            {"role": "assistant", "tool_calls": [{"id": "write", "function": {"name": "write_file", "arguments": '{"path":"value.txt","content":"new"}'}}]},
            {"role": "assistant", "content": "claimed success"},
            {"role": "assistant", "tool_calls": [{"id": "test2", "function": {"name": "run_command", "arguments": '{"command":"python -m unittest discover -s tests -v"}'}}]},
            {"role": "assistant", "content": "verified"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "tests").mkdir()
            (workspace / "tests" / "test_ok.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n", encoding="utf-8")
            result = CodingAgent(workspace, client).run("fix then test")
        self.assertTrue(result.startswith("verified"))
        self.assertIn("最后一次成功测试后又发生了文件修改", client.calls[3][-1]["content"])

    def test_no_tools_request_skips_calls_and_automatic_git_review(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "read", "function": {"name": "list_files", "arguments": "{}"}}]},
            {"role": "assistant", "content": "只回答问题"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client).run("不要执行任何工具，只回答问题")
        self.assertTrue(result.startswith("只回答问题"))
        self.assertIn("未执行自动 Git 审查", result)
        self.assertIn("工具已被用户禁止", client.calls[1][-1]["content"])

    def test_task_constraint_blocks_test_file_edits(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "write", "function": {"name": "write_file", "arguments": '{"path":"tests/test_x.py","content":"x"}'}}]},
            {"role": "assistant", "content": "done"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client).run("不要修改测试，只修实现")
        self.assertTrue(result.startswith("done"))
        self.assertIn("禁止修改测试文件", client.calls[1][-1]["content"])

    def test_equivalent_tests_directory_constraint_blocks_before_approval(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "write", "function": {"name": "write_file", "arguments": '{"path":"tests/test_x.py","content":"x"}'}}]},
            {"role": "assistant", "content": "done"},
        ])
        approvals = []
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client, approval_callback=lambda *args: approvals.append(args) or True).run("不要修改 tests 下任何文件，只修实现")
        self.assertTrue(result.startswith("done"))
        self.assertFalse(approvals)
        self.assertIn("禁止修改测试文件", client.calls[1][-1]["content"])

    def test_new_task_resets_plan_but_keeps_chat_history(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "plan", "function": {"name": "update_plan", "arguments": '{"steps":[{"step":"Old task","status":"in_progress"}]}'}}]},
            {"role": "assistant", "content": "first done"},
            {"role": "assistant", "content": "second done"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            agent.run("first task")
            result = agent.run("second task")
        self.assertIn("当前计划：未创建计划", result)
        self.assertEqual(agent.plan, [])
        self.assertTrue(any(message.get("content") == "first task" for message in client.calls[2]))

    def test_modified_files_are_unique_while_version_increments(self):
        client = FakeClient([
            {"role": "assistant", "tool_calls": [{"id": "one", "function": {"name": "write_file", "arguments": '{"path":"same.py","content":"one"}'}}]},
            {"role": "assistant", "tool_calls": [{"id": "two", "function": {"name": "write_file", "arguments": '{"path":"same.py","content":"two"}'}}]},
            {"role": "assistant", "content": "done"},
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = CodingAgent(Path(directory), client).run("edit twice")
        self.assertIn("修改的文件：same.py", result)
        self.assertIn("当前代码修改版本：2", result)
        self.assertEqual(result.count("same.py"), 1)

    def test_chinese_task_sets_chinese_response_instruction(self):
        client = FakeClient([{"role": "assistant", "content": "完成"}])
        with tempfile.TemporaryDirectory() as directory:
            CodingAgent(Path(directory), client).run("请用中文说明项目")
        self.assertIn("reply in Chinese", client.calls[0][0]["content"])

    def test_reset_clears_policy_and_verification_state(self):
        client = FakeClient([])
        with tempfile.TemporaryDirectory() as directory:
            agent = CodingAgent(Path(directory), client)
            agent._denied_operations.add("command:test")
            agent._session_mutations.add("x.py")
            agent._mutation_version = 2
            agent._last_verified_mutation_version = 1
            agent._tools_forbidden = True
            agent.reset()
        self.assertFalse(agent._denied_operations)
        self.assertFalse(agent._session_mutations)
        self.assertEqual(agent._mutation_version, 0)
        self.assertEqual(agent._last_verified_mutation_version, -1)
        self.assertFalse(agent._tools_forbidden)


if __name__ == "__main__":
    unittest.main()
