"""Test the installed OpenAI SDK through httpx.MockTransport; no network or real key."""
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from agent_lab.config import Settings
from agent_lab.engine import Engine
from agent_lab.providers import ModelRequest, OpenAIProvider, ProviderError
from agent_lab.schemas import Contribution, FinalAnswer
from agent_lab.storage import RunStore


def response_json(text, status="completed"):
    return {
        "id": "resp_test", "object": "response", "created_at": 1, "status": status,
        "model": "gpt-4.1-mini", "parallel_tool_calls": True,
        "tool_choice": "auto", "tools": [],
        "output": [{"id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": text, "annotations": []}]}],
        "usage": {"input_tokens": 11, "output_tokens": 5, "total_tokens": 16},
    }


class SDKContract(unittest.IsolatedAsyncioTestCase):
    def provider(self, handler, settings=None):
        client = AsyncOpenAI(
            api_key="not-a-real-key-for-unit-test", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            base_url="https://api.openai.com/v1",
        )
        provider = OpenAIProvider(settings or Settings(provider="openai"), client=client)
        self.addAsyncCleanup(provider.close)
        return provider

    async def test_sdk_serializes_strict_schema_and_parses_usage(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response_json(json.dumps({
                "content": "Có giải pháp", "next_agent": "reviewer", "handoff_note": "Kiểm tra"})))
        provider = self.provider(handler, Settings(role_models={"builder": "configured-model"}))
        result = await provider.generate(ModelRequest("builder", "Role instruction", {"task": "test"}, Contribution, 1200))
        self.assertEqual(result.parsed.next_agent, "reviewer")
        self.assertEqual((result.input_tokens, result.output_tokens), (11, 5))
        self.assertEqual(requests[0].url.path, "/v1/responses")
        body = json.loads(requests[0].content)
        self.assertEqual(body["model"], "configured-model")
        self.assertFalse(body["store"])
        fmt = body["text"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertTrue(fmt["strict"])
        self.assertFalse(fmt["schema"]["additionalProperties"])
        self.assertEqual(set(fmt["schema"]["required"]), {"content", "next_agent", "handoff_note"})

    async def test_incomplete_and_invalid_json_keep_usage_and_fail_clearly(self):
        for text, status in (("", "incomplete"), ("not json", "completed")):
            with self.subTest(status=status):
                provider = self.provider(lambda req: httpx.Response(200, json=response_json(text, status)))
                with self.assertRaises(ProviderError) as caught:
                    await provider.generate(ModelRequest("finalizer", "Test", {}, FinalAnswer, 256))
                self.assertFalse(caught.exception.retryable)
                self.assertEqual(caught.exception.input_tokens, 11)

    async def test_refusal_is_not_treated_as_success(self):
        data = response_json("")
        data["output"][0]["content"] = [{"type": "refusal", "refusal": "No"}]
        provider = self.provider(lambda req: httpx.Response(200, json=data))
        with self.assertRaisesRegex(ProviderError, "tu choi"):
            await provider.generate(ModelRequest("finalizer", "Test", {}, FinalAnswer, 256))

    async def test_error_mapping_does_not_echo_server_secrets(self):
        for status, code, retry in ((401, "invalid_api_key", False),
                                    (429, "insufficient_quota", False),
                                    (429, "rate_limit_exceeded", True),
                                    (500, "server_error", True)):
            with self.subTest(status=status, code=code):
                provider = self.provider(lambda req: httpx.Response(status, json={"error": {
                    "message": "private-sensitive-message", "type": code, "code": code}}))
                with self.assertRaises(ProviderError) as caught:
                    await provider.generate(ModelRequest("finalizer", "Test", {}, FinalAnswer, 256))
                self.assertEqual(caught.exception.retryable, retry)
                self.assertNotIn("private-sensitive", str(caught.exception))

    async def test_retry_counts_every_http_attempt_and_stays_within_budget(self):
        count = 0
        def handler(req):
            nonlocal count
            count += 1
            if count == 1:
                return httpx.Response(429, json={"error": {"message": "rate", "code": "rate_limit_exceeded"}})
            return httpx.Response(200, json=response_json(json.dumps({
                "content": "OK", "next_agent": "builder", "handoff_note": "go"})))
        provider = self.provider(handler)
        with tempfile.TemporaryDirectory() as tmp:
            engine = Engine(Settings(max_calls=2, max_turns=1), provider,
                            RunStore(Path(tmp) / "run", quiet=True), "Test", [], [], "handoff")
            state = await engine.run()
        self.assertEqual(count, 2)
        self.assertEqual(state["usage"]["calls_attempted"], 2)
        self.assertEqual(state["usage"]["input_tokens"], 11)
        self.assertEqual(state["status"], "limit_reached")


if __name__ == "__main__":
    unittest.main()
