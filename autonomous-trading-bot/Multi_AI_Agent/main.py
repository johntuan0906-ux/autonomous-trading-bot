import argparse
import asyncio
import importlib.metadata
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent_lab.config import ConfigurationError, Settings
from agent_lab.context import load_context
from agent_lab.engine import Engine
from agent_lab.providers import MockProvider, ModelRequest, OpenAIProvider, ProviderError
from agent_lab.schemas import FinalAnswer
from agent_lab.storage import RunStore

ROOT = Path(__file__).resolve().parent


def parser() -> argparse.ArgumentParser:
    app = argparse.ArgumentParser(description="Multi-AI Agent: Group Chat, Hand-off, Parallel. Doc README.md de bat dau.")
    commands = app.add_subparsers(dest="command", required=True)
    check = commands.add_parser("doctor", help="Kiem tra cai dat; mac dinh khong goi API")
    check.add_argument("--live", action="store_true", help="Goi 1 request API nho, co the tinh phi")
    run = commands.add_parser("run", help="Thuc hien 1 nhiem vu bang nhom agent")
    run.add_argument("--mode", choices=("group", "handoff", "parallel"), default="handoff")
    run.add_argument("--provider", choices=("mock", "openai"))
    task = run.add_mutually_exclusive_group(required=True)
    task.add_argument("--task", help="Mo ta nhiem vu; dat trong dau ngoac kep")
    task.add_argument("--task-file", help="File UTF-8 chua nhiem vu")
    run.add_argument("--context", action="append", default=[], metavar="FILE",
                     help="File noi dung gui cho AI; co the lap --context nhieu lan")
    run.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    return app


async def doctor(settings: Settings, live: bool) -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Interpreter: {sys.executable}")
    for name in ("openai", "pydantic", "python-dotenv"):
        print(f"{name}: {importlib.metadata.version(name)}")
    print(f".env canh main.py: {'co' if (ROOT / '.env').is_file() else 'chua co'}")
    print(f"OPENAI_API_KEY: {'da cau hinh (an gia tri)' if settings.api_key else 'chua cau hinh'}")
    print(f"Model mac dinh: {settings.model}; model kiem tra: {settings.model_for('finalizer')}")
    print(f"MAX_CALLS={settings.max_calls}, MAX_TURNS={settings.max_turns}, MAX_CONCURRENCY={settings.max_concurrency}")
    if not live:
        print("Kiem tra cuc bo OK. Chua xac minh API key, so du, model hay ket noi. Dung doctor --live de kiem tra API.")
        return 0
    provider = OpenAIProvider(settings)
    try:
        async with asyncio.timeout(settings.request_timeout):
            result = await provider.generate(ModelRequest(
                "finalizer", "Kiem tra API. Tra answer_markdown la OK va limitations la mang rong.",
                {"task": "Kiem tra ket noi va structured output."}, FinalAnswer, 128,
            ))
        print("API va schema OK. Chi da kiem tra model finalizer; cac model vai tro khac se duoc kiem tra khi run.")
        print(f"input_tokens={result.input_tokens}, output_tokens={result.output_tokens}")
        return 0
    finally:
        await provider.close()


async def run_job(args, settings: Settings) -> int:
    if args.task_file:
        texts, _ = load_context([args.task_file], 6000)
        task = texts[0]["text"].strip()
    else:
        task = args.task.strip()
    if not task or len(task) > 6000:
        raise ValueError("Nhiem vu phai co 1..6000 ky tu.")
    context, metadata = load_context(args.context, settings.max_context_chars)
    if settings.provider == "openai":
        print("OPENAI: goi AI that, tinh phi theo tai khoan API.")
        if metadata:
            print("File se gui cho API: " + ", ".join(row["file"] for row in metadata))
        provider = OpenAIProvider(settings)
    else:
        print("MO PHONG: cau tra loi co dinh; khong goi AI, khong ton phi API.")
        provider = MockProvider()
    try:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
        store = RunStore(args.output_dir.expanduser().resolve() / run_id)
        print(f"Ket qua: {store.path}", flush=True)
        engine = Engine(settings, provider, store, task, context, metadata, args.mode)
        state = await engine.run()
        print(f"\nTrang thai: {state['status']}; so lan goi: {state['usage']['calls_attempted']}")
        print(f"Mo {store.path / 'report.md'} de xem ket qua.")
        for error in state["errors"]:
            print("Loi: " + error, file=sys.stderr)
        return 0 if state["status"] == "completed" else 2
    finally:
        await provider.close()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    try:
        settings = Settings.from_env(ROOT, getattr(args, "provider", None))
        if args.command == "doctor":
            return asyncio.run(doctor(settings, args.live))
        return asyncio.run(run_job(args, settings))
    except KeyboardInterrupt:
        print("\nDa dung. Neu run da bat dau, xem report/transcript trong thu muc ket qua vua in.")
        return 130
    except TimeoutError:
        print("Loi: het thoi gian cho API. Kiem tra ket noi/cau hinh timeout.", file=sys.stderr)
        return 2
    except (ConfigurationError, ProviderError, ValueError, OSError) as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
