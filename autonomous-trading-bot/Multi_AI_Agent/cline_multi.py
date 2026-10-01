"""Run: python cline_multi.py --help"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from agent_lab.clinepass import ClineClient, Limits, MockClient, ParallelRun, read_catalog
from agent_lab.context import load_context

ROOT = Path(__file__).resolve().parent


def parser():
    p = argparse.ArgumentParser(description="ClinePass: nhiều model song song, một kết quả tổng hợp.")
    p.add_argument("command", choices=["list", "check", "run"])
    p.add_argument("--provider", choices=["mock", "clinepass"], default="mock",
                   help="Mặc định mock, không gọi API.")
    p.add_argument("--models-file", type=Path, default=ROOT / "models.clinepass.json")
    p.add_argument("--group", choices=["core", "all"], default="core")
    p.add_argument("--model", action="append", help="Chọn ID có trong catalog; lặp lại để chọn nhiều.")
    p.add_argument("--concurrency", type=int, help="Tối đa bao nhiêu request cùng lúc.")
    task = p.add_mutually_exclusive_group()
    task.add_argument("--task")
    task.add_argument("--task-file", type=Path)
    p.add_argument("--context", action="append", default=[], help="File UTF-8 gửi cho các agent.")
    p.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    return p


async def execute(args, agents, finalizer, limits, task, context, metadata, output):
    def runner(client):
        return ParallelRun(client=client, agents=agents, finalizer=finalizer, limits=limits,
                           task=task, context=context, metadata=metadata, provider=args.provider,
                           output=output, check_only=args.command == "check")
    if args.provider == "mock":
        return await runner(MockClient()).run()
    async with httpx.AsyncClient(timeout=limits.request_timeout, follow_redirects=False,
                                 limits=httpx.Limits(max_connections=limits.concurrency)) as http:
        return await runner(ClineClient(http, os.getenv("CLINE_API_KEY", ""))).run()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env", override=False, encoding="utf-8-sig")
    args = parser().parse_args()
    try:
        catalog, finalizer = read_catalog(args.models_file)
        if args.command == "list":
            for agent in catalog:
                print(f"{'[core]' if agent.core else '      '} {agent.model}: {agent.role}")
            print(f"\nModel tổng hợp: {finalizer}")
            return 0
        if args.model:
            selected = set(args.model)
            if selected - {a.model for a in catalog}:
                raise ValueError("Có ID chưa có trong models.clinepass.json; dùng lệnh list để xem.")
            agents = [a for a in catalog if a.model in selected]
        else:
            agents = [a for a in catalog if args.group == "all" or a.core]
        if not agents:
            raise ValueError("Không có agent được chọn.")
        limits = Limits(
            concurrency=args.concurrency if args.concurrency is not None else int(os.getenv("CLINE_CONCURRENCY", "3")),
            request_timeout=float(os.getenv("CLINE_REQUEST_TIMEOUT", "180")),
            run_timeout=float(os.getenv("CLINE_RUN_TIMEOUT", "900")),
            max_retries=int(os.getenv("CLINE_MAX_RETRIES", "2")),
            max_calls=int(os.getenv("CLINE_MAX_CALLS", "45")),
            summary_chars=int(os.getenv("CLINE_SUMMARY_CHARS_PER_AGENT", "6000")),
        )
        limits.validate()
        if limits.max_calls < len(agents) + (args.command == "run"):
            raise ValueError("CLINE_MAX_CALLS cần đủ cho các agent và lượt tổng hợp.")
        if args.command == "check":
            if args.context or args.task or args.task_file:
                raise ValueError("check chỉ kiểm tra API, không nhận task/context. Dùng run cho công việc.")
            task, context, metadata = "Kiểm tra kết nối từng model", [], []
        else:
            if args.task_file:
                task_parts, _ = load_context([str(args.task_file)], 6000)
                task = task_parts[0]["text"]
            else:
                task = args.task or ""
            if not task.strip() or len(task) > 6000:
                raise ValueError("Cần --task hoặc --task-file, tối đa 6000 ký tự.")
            context, metadata = load_context(args.context, int(os.getenv("CLINE_MAX_CONTEXT_CHARS", "20000")))
        if args.provider == "clinepass" and not os.getenv("CLINE_API_KEY", "").strip():
            raise ValueError("Thiếu CLINE_API_KEY trong .env. Mock không cần key.")
        output = args.output_dir / (datetime.now(timezone.utc).strftime("clinepass_%Y%m%d_%H%M%S_") + uuid4().hex[:8])
        print(f"Provider={args.provider}; số agent={len(agents)}; concurrency={limits.concurrency}.")
        print(f"Kết quả sẽ lưu tại: {output.resolve()}", flush=True)
        state = asyncio.run(execute(args, agents, finalizer, limits, task, context, metadata, output))
        return 0 if state["status"] == "completed" else 1
    except KeyboardInterrupt:
        print("Đã ngắt. Kết quả nhận được trước đó được lưu trong thư mục đã in ở trên.")
        return 130
    except ImportError:
        print("Thiếu thư viện bổ sung. Nếu dùng SOCKS proxy, cài httpx[socks]==0.28.1.", file=sys.stderr)
        return 2
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(f"Lỗi cấu hình/file: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
