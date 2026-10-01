import asyncio
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agent_lab.config import Settings
from agent_lab.context import load_context
from agent_lab.engine import Engine
from agent_lab.providers import MockProvider, ModelResult, ProviderError
from agent_lab.schemas import Contribution, Decision, FinalAnswer
from agent_lab.storage import RunStore


class CaptureMock(MockProvider):
    def __init__(self):
        self.requests = []
        self.active = self.peak = 0

    async def generate(self, request):
        self.requests.append(request)
        self.active += 1
        self.peak = max(self.active, self.peak)
        try:
            return await super().generate(request)
        finally:
            self.active -= 1


class Workflows(unittest.IsolatedAsyncioTestCase):
    def make_engine(self, mode="handoff", provider=None, **settings):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = RunStore(Path(tmp.name) / "run", quiet=True)
        return Engine(replace(Settings(), **settings), provider or CaptureMock(), store,
                      "Test mục tiêu", [{"file": "a.py", "text": "x = 1"}], [], mode)

    async def test_all_modes_terminate_and_persist_real_transcripts(self):
        for mode, calls in (("handoff", 4), ("group", 8), ("parallel", 4)):
            with self.subTest(mode=mode):
                engine = self.make_engine(mode)
                state = await engine.run()
                self.assertEqual(state["status"], "completed")
                self.assertEqual(state["usage"]["calls_attempted"], calls)
                self.assertEqual({x["agent"] for x in state["transcript"]}, {"planner", "builder", "reviewer"})
                on_disk = json.loads((engine.store.path / "transcript.json").read_text(encoding="utf-8"))
                self.assertEqual(on_disk, state)
                self.assertIn("MÔ PHỎNG", (engine.store.path / "report.md").read_text(encoding="utf-8"))

    async def test_group_broadcasts_prior_contributions_to_next_agent(self):
        provider = CaptureMock()
        await self.make_engine("group", provider).run()
        reviewer = next(r for r in provider.requests if r.role == "reviewer")
        self.assertEqual([x["agent"] for x in reviewer.payload["transcript"]], ["planner", "builder"])
        self.assertEqual(reviewer.payload["context"][0]["text"], "x = 1")

    async def test_group_rejects_premature_finish_and_requires_coverage(self):
        class EarlyFinish(MockProvider):
            async def generate(self, request):
                if request.schema is Decision:
                    return ModelResult(Decision(next_speaker="finish", instruction="Stop"))
                return await super().generate(request)
        state = await self.make_engine("group", EarlyFinish()).run()
        self.assertEqual([m["agent"] for m in state["transcript"]], ["planner", "builder", "reviewer"])
        self.assertEqual(state["status"], "completed")

    async def test_handoff_can_return_to_builder_for_revision(self):
        class ReviseOnce(MockProvider):
            reviews = 0
            async def generate(self, request):
                result = await super().generate(request)
                if request.role == "reviewer":
                    self.reviews += 1
                    if self.reviews == 1:
                        return ModelResult(Contribution(content="Cần sửa A", next_agent="builder", handoff_note="Sửa A"))
                if request.role == "builder" and self.reviews:
                    assert request.payload["transcript"][-1]["handoff_note"] == "Sửa A"
                return result
        state = await self.make_engine(provider=ReviseOnce()).run()
        self.assertEqual([x["agent"] for x in state["transcript"]], ["planner", "builder", "reviewer", "builder", "reviewer"])
        self.assertEqual(state["status"], "completed")

    async def test_invalid_handoff_does_not_execute_arbitrary_agent(self):
        class Invalid(MockProvider):
            async def generate(self, request):
                return ModelResult(Contribution(content="X", next_agent="finish", handoff_note="X"))
        state = await self.make_engine(provider=Invalid()).run()
        self.assertEqual(state["status"], "failed")
        self.assertIsNone(state["final"])
        self.assertEqual(state["usage"]["calls_attempted"], 1)

    async def test_parallel_is_concurrent_and_keeps_worker_inputs_independent(self):
        provider = CaptureMock()
        state = await self.make_engine("parallel", provider, max_concurrency=2).run()
        self.assertEqual(provider.peak, 2)
        workers = [r for r in provider.requests if r.role != "finalizer"]
        self.assertTrue(all(not r.payload["transcript"] for r in workers))
        final = next(r for r in provider.requests if r.role == "finalizer")
        self.assertEqual(len(final.payload["transcript"]), 3)
        self.assertEqual(state["status"], "completed")

    async def test_failed_parallel_worker_is_disclosed_in_summary_input(self):
        class FailingReviewer(CaptureMock):
            async def generate(self, request):
                if request.role == "reviewer":
                    raise ProviderError("reviewer unavailable")
                return await super().generate(request)
        provider = FailingReviewer()
        state = await self.make_engine("parallel", provider).run()
        self.assertEqual(state["status"], "partial")
        self.assertEqual(len(state["transcript"]), 2)
        self.assertIsNotNone(state["final"])
        final = next(r for r in provider.requests if r.schema is FinalAnswer)
        self.assertIn("reviewer", final.payload["errors"][0])

    async def test_budget_is_atomic_even_with_parallel_calls(self):
        state = await self.make_engine("parallel", max_calls=2).run()
        self.assertEqual(state["usage"]["calls_attempted"], 2)
        self.assertEqual(state["status"], "limit_reached")
        self.assertIsNone(state["final"])

    async def test_turn_limit_saves_partial_work_and_labels_it(self):
        state = await self.make_engine(max_turns=1).run()
        self.assertEqual(state["status"], "limit_reached")
        self.assertEqual(len(state["transcript"]), 1)
        self.assertIsNotNone(state["final"])

    async def test_global_timeout_cancels_parallel_workers_and_saves_work(self):
        class Slow(MockProvider):
            active = 0
            async def generate(self, request):
                self.active += 1
                try:
                    await asyncio.sleep(30)
                finally:
                    self.active -= 1
        provider = Slow()
        engine = self.make_engine("parallel", provider, run_timeout=1)
        state = await engine.run()
        self.assertEqual(state["status"], "limit_reached")
        self.assertEqual(provider.active, 0)
        self.assertTrue((engine.store.path / "report.md").is_file())

    async def test_external_cancellation_persists_interrupted_state(self):
        class Wait(MockProvider):
            started = asyncio.Event()
            async def generate(self, request):
                self.started.set()
                await asyncio.sleep(30)
        provider = Wait()
        engine = self.make_engine(provider=provider)
        task = asyncio.create_task(engine.run())
        await provider.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        data = json.loads((engine.store.path / "transcript.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "interrupted")


class ContextTests(unittest.TestCase):
    def test_only_selected_utf8_files_are_loaded_and_secrets_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / "a.py"
            code.write_text("# tiếng Việt\nx = 1", encoding="utf-8")
            context, meta = load_context([str(code), str(code)], 100)
            self.assertEqual(len(context), 1)
            self.assertEqual(len(meta[0]["sha256"]), 64)
            secret = root / ".env"
            secret.write_text("KEY=test", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_context([str(secret)], 100)
            with self.assertRaises(ValueError):
                load_context([str(code)], 2)


if __name__ == "__main__":
    unittest.main()
