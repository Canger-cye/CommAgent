#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "[CommAgent] 启动中..."
python run.py --llm "${1:-mock}" --port "${2:-8787}"
