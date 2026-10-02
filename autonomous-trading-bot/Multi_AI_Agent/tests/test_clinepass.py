import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import httpx

from agent_lab.clinepass import (
    Agent, CallFailure, ClineClient, ENDPOINT, Limits, ParallelRun, Reply, read_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG, FINALIZER = read_catalog(ROOT / "models.clinepass.json")


class ClineCLITests(unittest.TestCase):
    def test_mock_all_14_works_without_http_client_or_valid_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.run([sys.executable, str(ROOT / "cline_multi.py"),
                "run", "--provider", "mock", "--group", "all", "--concurrency", "14",
                "--task", "Kiá»ƒm tra cháº¡y offline", "--output-dir", directory],
                env={**os.environ, "ALL_PROXY": "unsupported-test-proxy://localhost:1"},
                capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            runs = list(Path(directory).glob("*/run.json"))
            self.assertEqual(len(runs), 1)
            state = json.loads(runs[0].read_text(encoding="utf-8"))
            self.assertEqual(state["provider"], "mock")
            self.assertEqual(state["calls_attempted"], 15)


def api_response(request, *, finish="stop", content="BÃ¡o cÃ¡o thá»­ nghiá»‡m", status=200):
    model = json.loads(request.content)["model"]
    return httpx.Response(status, json={"model": model,
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20}})


class ClineTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_endpoint_authorization_model_and_nonstreaming(self):
        def handler(request):
            self.assertEqual(str(request.url), ENDPOINT)
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.headers["Authorization"], "Bearer dummy-test-key")
            body = json.loads(request.content)
            self.assertEqual(body, {"model": CATALOG[0].model,
                "messages": [{"role": "user", "content": "OK"}], "stream": False})
            return api_response(request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            result = await ClineClient(http, "dummy-test-key").complete(
                CATALOG[0].model, [{"role": "user", "content": "OK"}])
        self.assertEqual((result.input_tokens, result.output_tokens), (10, 20))

    async def test_error_categories_and_no_secret_echo(self):
        for code, retryable in [(400, False), (401, False), (402, False),
                                 (403, False), (404, False), (429, True), (503, True)]:
            with self.subTest(code=code):
                async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda request: httpx.Response(code, headers={"Retry-After": "2"},
                        json={"error": {"message": "dummy-secret-never-print"}}))) as http:
                    with self.assertRaises(CallFailure) as caught:
                        await ClineClient(http, "dummy-secret-never-print").complete(CATALOG[0].model, [])
                self.assertEqual(caught.exception.retryable, retryable)
                self.assertEqual(caught.exception.retry_after, 2)
                self.assertNotIn("dummy-secret-never-print", str(caught.exception))

    async def test_bad_json_and_non_pass_model_are_rejected(self):
        sent = 0
        def handler(request):
            nonlocal sent
            sent += 1
            return httpx.Response(200, text="not json")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = ClineClient(http, "test-key")
            with self.assertRaises(CallFailure):
                await client.complete("usage-billing/some-model", [])
            self.assertEqual(sent, 0)
            with self.assertRaises(CallFailure):
                await client.complete(CATALOG[0].model, [])


class ClineWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "run"

    def runner(self, client, agents=None, limits=None, check=False):
        return ParallelRun(client=client, agents=agents or CATALOG, finalizer=FINALIZER,
            limits=limits or Limits(concurrency=14, max_retries=0, request_timeout=5, run_timeout=10),
            task="ÄÃ¡nh giÃ¡ mÃ£ máº«u", context=[{"file": "sample.py", "text": "print(1)"}],
            metadata=[], provider="clinepass", output=self.output, check_only=check, quiet=True)

    async def test_all_14_overlap_then_finalizer_sees_every_result(self):
        started, finished, active, peak = 0, 0, 0, 0
        barrier = asyncio.Event()
        seen = []
        async def handler(request):
            nonlocal started, finished, active, peak
            body = json.loads(request.content)
            data = json.loads(body["messages"][-1]["content"])
            if "reports" in data:
                self.assertEqual(finished, 14)
                self.assertEqual(len(data["reports"]), 14)
                self.assertTrue(all(r["status"] == "ok" for r in data["reports"]))
            else:
                started += 1
                active += 1
                peak = max(peak, active)
                seen.append(body["model"])
                if started == 14:
                    barrier.set()
                await asyncio.wait_for(barrier.wait(), timeout=2)
                active -= 1
                finished += 1
            return api_response(request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            state = await self.runner(ClineClient(http, "test-key")).run()
        self.assertEqual(peak, 14)
        self.assertEqual(len(set(seen)), 14)
        self.assertEqual(state["calls_attempted"], 15)
        self.assertEqual(state["status"], "completed")
        saved = json.loads((self.output / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["finalizer"]["status"], "ok")

    async def test_concurrency_three_and_single_failure_preserves_other_results(self):
        active, peak = 0, 0
        seen = []
        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.005)
            active -= 1
            model = json.loads(request.content)["model"]
            seen.append(model)
            return api_response(request, status=404 if model == CATALOG[0].model else 200)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            state = await self.runner(ClineClient(http, "test-key"),
                                     limits=Limits(concurrency=3, max_retries=0)).run()
        self.assertEqual(peak, 3)
        self.assertEqual(state["status"], "partial")
        self.assertEqual(sum(r["status"] == "ok" for r in state["agents"]), 13)
        self.assertEqual(seen.count(CATALOG[0].model), 1)  # No fallback, no retry on 404.
        self.assertIn("HTTP 404", (self.output / "report.md").read_text(encoding="utf-8"))

    async def test_truncated_response_kept_but_not_marked_success(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: api_response(request, finish="length", content="Báº£n chÆ°a Ä‘áº§y Ä‘á»§"))) as http:
            state = await self.runner(ClineClient(http, "test-key"), agents=CATALOG[:1]).run()
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["agents"][0]["content"], "Báº£n chÆ°a Ä‘áº§y Ä‘á»§")
        self.assertEqual(state["agents"][0]["usage_received"]["output_tokens"], 20)
        self.assertIsNone(state["finalizer"])

    async def test_retry_is_counted_and_budget_not_exceeded(self):
        calls = 0
        async def handler(request):
            nonlocal calls
            calls += 1
            return api_response(request, status=429 if calls == 1 else 200)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            state = await self.runner(ClineClient(http, "test-key"), agents=CATALOG[:1],
                limits=Limits(concurrency=1, max_calls=2, max_retries=2)).run()
        self.assertEqual(calls, 2)
        self.assertEqual(state["calls_attempted"], 2)
        self.assertEqual(state["agents"][0]["status"], "ok")
        self.assertEqual(state["finalizer"]["status"], "error")
        self.assertEqual(state["status"], "partial")

    async def test_global_timeout_saves_finished_and_cancelled_workers(self):
        class SlowClient:
            async def complete(self, model, messages):
                if model == CATALOG[0].model:
                    return Reply("Nhanh", "stop", model)
                await asyncio.sleep(10)
        state = await self.runner(SlowClient(), agents=CATALOG[:2],
            limits=Limits(concurrency=2, run_timeout=0.06)).run()
        self.assertEqual(state["status"], "timeout")
        self.assertEqual([r["status"] for r in state["agents"]], ["ok", "cancelled"])
        self.assertTrue((self.output / "report.md").is_file())
        self.assertEqual(json.loads((self.output / "run.json").read_text(encoding="utf-8"))["status"], "timeout")

    async def test_cancellation_saves_partial_report(self):
        entered = asyncio.Event()
        class WaitingClient:
            async def complete(self, model, messages):
                entered.set()
                await asyncio.Event().wait()
        runner = self.runner(WaitingClient(), agents=CATALOG[:1])
        task = asyncio.create_task(runner.run())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(runner.state["status"], "interrupted")
        self.assertIn("interrupted", (self.output / "report.md").read_text(encoding="utf-8"))

    async def test_check_does_not_call_finalizer(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(api_response)) as http:
            state = await self.runner(ClineClient(http, "test-key"), agents=CATALOG[:2], check=True).run()
        self.assertEqual(state["calls_attempted"], 2)
        self.assertEqual(state["status"], "completed")
        self.assertIsNone(state["finalizer"])

    async def test_summary_clipping_is_disclosed_and_full_content_preserved(self):
        full_text = "A" * 700
        class LongClient:
            async def complete(inner_self, model, messages):
                payload = json.loads(messages[-1]["content"])
                if "reports" in payload:
                    self.assertTrue(payload["reports"][0]["excerpt_clipped"])
                    self.assertEqual(len(payload["reports"][0]["content"]), 500)
                    return Reply("Tá»•ng há»£p", "stop", model)
                return Reply(full_text, "stop", model)
        state = await self.runner(LongClient(), agents=CATALOG[:1], limits=Limits(summary_chars=500)).run()
        self.assertEqual(state["agents"][0]["content"], full_text)
        self.assertEqual(len(state["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
