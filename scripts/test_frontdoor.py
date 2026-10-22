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


class PolicyAndGuardTests(unittest.TestCase):
    CONTROLLER = {"controller": {"enabled": True, "require_full_workflow": True}}

    def test_controller_forces_full_pipeline(self):
        r = fd(ScriptedLLM([]), config=self.CONTROLLER).handle("hello")
        self.assertEqual(r.mode, "full")
        self.assertEqual(r.steps[-1].tool, "m1frame_run")

    def test_controller_refuses_quick_chat(self):
        with self.assertRaises(ValueError):
            fd(ScriptedLLM([]), config=self.CONTROLLER).handle("/quick hi")

    def test_default_mode_from_config(self):
        r = fd(ScriptedLLM([]), default_mode="full").handle("plan it")
        self.assertEqual(r.mode, "full")

    def test_tool_results_pass_ingest_guard(self):
        reg = registry()
        reg.register(Tool("leak", "x", lambda: "key AKIAABCDEFGHIJKLMNOP here", {}))
        llm = ScriptedLLM(['{"m1frame_tool":"leak","arguments":{}}', "done"])
        FrontDoor(llm, reg, workflow=lambda g: {}, wiki=lambda q, n=3: "", context=lambda q="": {}).handle("go")
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", llm.calls[1]["prompt"])

    def test_backend_is_passed_to_pipeline(self):
        import frontdoor.agent as agent_mod
        seen = {}
        original = agent_mod._default_workflow
        agent_mod._default_workflow = lambda goal, backend=None: seen.setdefault("b", backend) and {"output": ""}
        try:
            llm = ScriptedLLM([])
            llm.backend = "ollama"
            FrontDoor(llm, registry(), wiki=lambda q, n=3: "", context=lambda q="": {}).handle("/run x")
        finally:
            agent_mod._default_workflow = original
        self.assertEqual(seen["b"], "ollama")


class IntegrationSurfaceTests(unittest.TestCase):
    def test_register_routes_on_existing_app(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from frontdoor.openai_server import register_routes
        app = FastAPI()
        register_routes(app, lambda: fd(ScriptedLLM(["ok"])))
        res = TestClient(app).post("/v1/chat/completions", json={
            "messages": [{"role": "user", "content": "hi"}]}).json()
        self.assertTrue(res["choices"][0]["message"]["content"].startswith("ok"))

    def test_standalone_key_required(self):
        from fastapi.testclient import TestClient
        client = TestClient(build_app(lambda: fd(ScriptedLLM(["ok"])), key="secret"))
        self.assertEqual(client.get("/v1/models").status_code, 401)
        self.assertEqual(client.get("/v1/models", headers={"Authorization": "Bearer secret"}).status_code, 200)

    def test_policy_refusal_is_http_400(self):
        from fastapi.testclient import TestClient
        agent = fd(ScriptedLLM([]), config=PolicyAndGuardTests.CONTROLLER)
        client = TestClient(build_app(lambda: agent, key=""))
        r = client.post("/v1/chat/completions", json={"model": "m1frame-chat",
                        "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(r.status_code, 400)

    def test_gateway_handler_uses_agent(self):
        from gateways.handlers import make_default_handler
        from gateways.router import GatewayRouter, InboundMessage
        router = GatewayRouter(handler=make_default_handler(agent=fd(ScriptedLLM(["agent reply"]))))
        self.assertIn("agent reply", router.handle(InboundMessage(text="hello")).text)
        full = GatewayRouter(handler=make_default_handler(agent=fd(ScriptedLLM([]))))
        self.assertIn("PIPELINE:build x", full.handle(InboundMessage(text="/run build x")).text)

    def test_gateway_without_agent_stays_offline(self):
        from gateways.handlers import make_default_handler
        from gateways.router import InboundMessage
        out = make_default_handler()(InboundMessage(text="m1frame"))
        self.assertIsInstance(out, str)

    def test_mcp_server_exposes_routing_and_agent(self):
        try:
            import mcp_server
        except SystemExit:
            self.skipTest("mcp SDK not installed")
        import asyncio
        self.assertIn("m1frame_run", mcp_server.ROUTING_INSTRUCTIONS)
        names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
        self.assertIn("m1frame_agent", names)
        prompts = {p.name for p in asyncio.run(mcp_server.mcp.list_prompts())}
        self.assertIn("m1frame", prompts)


class StudioServerTests(unittest.TestCase):
    def test_studio_serves_v1_models(self):
        from fastapi.testclient import TestClient

        from api.server import create_app
        with TestClient(create_app()) as client:
            ids = [m["id"] for m in client.get("/v1/models").json()["data"]]
        self.assertEqual(set(ids), {"m1frame", "m1frame-full", "m1frame-chat"})


if __name__ == "__main__":
    unittest.main()
