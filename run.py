#!/usr/bin/env python
"""CommAgent 一键启动脚本。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="CommAgent 启动器")
    parser.add_argument("--host", default=os.getenv("COMMAGENT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("COMMAGENT_PORT", "8787")))
    parser.add_argument("--llm", choices=["mock", "api"], default=os.getenv("COMMAGENT_LLM_MODE", "mock"))
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    args = parser.parse_args()

    os.environ["COMMAGENT_LLM_MODE"] = args.llm

    import uvicorn

    print("=" * 56)
    print("  CommAgent · 6G通感算智网络智能运维体")
    print(f"  LLM 模式 : {args.llm}")
    print(f"  访问地址 : http://{args.host}:{args.port}")
    print("=" * 56)

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
