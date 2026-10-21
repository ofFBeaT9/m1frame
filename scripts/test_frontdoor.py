"""Offline tests for the portable front door (no API key, no network)."""
import unittest

from frontdoor import FrontDoor, parse_tool_call
from frontdoor.openai_server import build_app, split_messages
from tools.registry import Tool, ToolRegistry


class ScriptedLLM:
    """Replays canned replies; records what it was sent."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, prompt, system="", temperature=None, max_tokens=None, history=None, model=None):
        self.calls.append({"prompt": prompt, "system": system, "history": list(history or [])})
        return self.replies.pop(0)


def registry():
    reg = ToolRegistry()
    reg.register(Tool("calculator", "math", lambda expression: eval(expression, {"__builtins__": {}}),
                      {"expression": "string"}))
    reg.register(Tool("write_file", "write", lambda path, content: {"ok": True},
                      {"path": "string", "content": "string"}, dangerous=True))
    return reg


def fd(llm, **kw):
    return FrontDoor(llm, registry(), workflow=lambda g: {"output": f"PIPELINE:{g}", "score": 8,
                     "approved": True, "receipt": "r1"},
                     wiki=lambda q, n=3: "no prior pages", context=lambda q="": {}, **kw)


class ProtocolTests(unittest.TestCase):
    known = {"calculator", "m1frame_run"}

    def test_exact_contract(self):
        self.assertEqual(parse_tool_call('{"m1frame_tool":"calculator","arguments":{"expression":"2+2"}}'),
                         ("calculator", {"expression": "2+2"}))

    def test_fenced_json_gpt_style(self):
        raw = 'Sure! I will calculate.\n```json\n{"m1frame_tool": "calculator", "arguments": {"expression": "6*7"}}\n```'
        self.assertEqual(parse_tool_call(raw, self.known), ("calculator", {"expression": "6*7"}))

    def test_drifted_keys_llama_style(self):
        raw = '{"name": "calculator", "parameters": {"expression": "1+1"}}'
        self.assertEqual(parse_tool_call(raw, self.known), ("calculator", {"expression": "1+1"}))

    def test_string_arguments(self):
        raw = '{"tool": "calculator", "arguments": "{\\"expression\\": \\"3\\"}"}'
        self.assertEqual(parse_tool_call(raw, self.known), ("calculator", {"expression": "3"}))

    def test_plain_json_deliverable_is_not_a_call(self):
        self.assertIsNone(parse_tool_call('{"name": "Alice", "age": 3}', self.known))
        self.assertIsNone(parse_tool_call("The answer is 42.", self.known))

    def test_braces_inside_strings(self):
        raw = 'x {"m1frame_tool":"calculator","arguments":{"expression":"\\"}{\\""}}'
        self.assertEqual(parse_tool_call(raw)[0], "calculator")


class FrontDoorTests(unittest.TestCase):
    def test_direct_answer_no_tools(self):
        r = fd(ScriptedLLM(["Hi there."])).handle("hello")
        self.assertEqual((r.answer, r.steps), ("Hi there.", []))

    def test_tool_then_answer_with_messy_model(self):
        llm = ScriptedLLM(['Let me compute that:\n```json\n{"m1frame_tool":"calculator","arguments":{"expression":"6*7"}}\n```',
                           "It is 42."])
        r = fd(llm).handle("what is 6*7")
        self.assertEqual(r.answer, "It is 42.")
        self.assertEqual([s.tool for s in r.steps], ["calculator"])
        self.assertIn("42", llm.calls[1]["prompt"])

    def test_agent_routes_to_pipeline(self):
        llm = ScriptedLLM(['{"m1frame_tool":"m1frame_run","arguments":{"goal":"design auth"}}', "Done: see plan."])
        r = fd(llm).handle("design an auth system")
        self.assertEqual(r.workflow["receipt"], "r1")
        self.assertIn("m1frame_run", r.receipt())

    def test_full_mode_is_enforced_without_model(self):
        llm = ScriptedLLM([])  # the model is never asked whether to run the pipeline
        r = fd(llm).handle("/run build a CLI")
        self.assertEqual(r.answer, "PIPELINE:build a CLI")
        self.assertEqual([s.tool for s in r.steps], ["wiki_query", "m1frame_run"])

    def test_dangerous_tool_denied_by_default(self):
        llm = ScriptedLLM(['{"m1frame_tool":"write_file","arguments":{"path":"a","content":"b"}}', "Could not write."])
        r = fd(llm).handle("write a file")
        self.assertFalse(r.steps[0].ok)
        self.assertIn("approval", llm.calls[1]["prompt"])

    def test_dangerous_tool_with_approval(self):
        llm = ScriptedLLM(['{"m1frame_tool":"write_file","arguments":{"path":"a","content":"b"}}', "Wrote it."])
        r = fd(llm, approve=lambda n, a: True).handle("write a file")
        self.assertTrue(r.steps[0].ok)

    def test_budget_forces_plain_answer(self):
        call = '{"m1frame_tool":"calculator","arguments":{"expression":"1"}}'
        llm = ScriptedLLM([call, call, call, "final"])
        r = fd(llm, max_steps=2).handle("loop")
        self.assertEqual((r.answer, len(r.steps)), ("final", 2))


class OpenAIServerTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        self.llm = ScriptedLLM(['{"m1frame_tool":"calculator","arguments":{"expression":"2+3"}}', "5"])
        self.client = TestClient(build_app(lambda: fd(self.llm)))

    def test_models(self):
        ids = [m["id"] for m in self.client.get("/v1/models").json()["data"]]
        self.assertIn("m1frame-full", ids)

    def test_completion_routes_through_frontdoor(self):
        res = self.client.post("/v1/chat/completions", json={"model": "m1frame",
                               "messages": [{"role": "user", "content": "2+3?"}]}).json()
        self.assertTrue(res["choices"][0]["message"]["content"].startswith("5"))
        self.assertEqual(res["m1frame"]["tools"], ["calculator"])

    def test_streaming(self):
        r = self.client.post("/v1/chat/completions", json={"model": "m1frame", "stream": True,
                             "messages": [{"role": "user", "content": "2+3?"}]})
        self.assertIn("[DONE]", r.text)

    def test_split_messages(self):
        prompt, hist = split_messages([{"role": "system", "content": "be brief"},
                                       {"role": "user", "content": "a"}, {"role": "assistant", "content": "b"},
                                       {"role": "user", "content": [{"type": "text", "text": "c"}]}])
        self.assertIn("be brief", prompt)
        self.assertTrue(prompt.endswith("c"))
        self.assertEqual(len(hist), 2)


class StoryLoopRegression(unittest.TestCase):
    def test_story_tool_loop_accepts_fenced_calls(self):
        from agents.tool_loop import run_with_tools
        llm = ScriptedLLM(['```json\n{"m1frame_tool":"calculator","arguments":{"expression":"9*9"}}\n```', "81"])
        out = run_with_tools(llm, "compute", "sys", config={"max_tool_calls": 2}, registry=registry())
        self.assertEqual(out, "81")
        self.assertIn("81", llm.calls[1]["prompt"])


if __name__ == "__main__":
    unittest.main()
