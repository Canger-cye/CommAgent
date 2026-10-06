# -*- coding: utf-8 -*-
"""闲聊 / 非专业对话应答测试。"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.agents import Orchestrator
from backend.llm.base import classify_intent


def post(path: str, payload: dict):
    req = urllib.request.Request(
        "http://127.0.0.1:8787" + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


CASES = [
    ("你好", "casual"),
    ("在吗", "casual"),
    ("谢谢", "casual"),
    ("哈哈", "casual"),
    ("你是谁", "casual"),
    ("讲个笑话", "casual"),
    ("今天有点累", "casual"),
    ("随便问问", "casual"),
    ("好的", "casual"),
    ("再见", "casual"),
    ("这个项目是干嘛的呀", "casual"),
    ("帮我做 3.5GHz 200m 的链路预算", "simulate_link"),
    ("SINR 是 -2dB，帮我诊断", "diagnose"),
    ("给我几个可以问的问题", "help"),
    ("什么是香农公式？", "knowledge"),
]


def main() -> None:
    o = Orchestrator()
    ok = 0
    print("=== classify ===")
    for text, expect in CASES:
        r = classify_intent(text)
        mark = "OK" if r["intent"] == expect else f"MISS exp={expect}"
        if r["intent"] == expect:
            ok += 1
        print(f"[{mark}] {r['intent']:18s} | {text}")

    print(f"\nclassify: {ok}/{len(CASES)}")

    print("\n=== orchestrator tone ===")
    for text in ["你好", "谢谢", "你是谁", "今天有点累", "讲个笑话"]:
        r = o.handle(text)
        assert r["intent"] == "casual", (text, r["intent"])
        assert r.get("light") is True
        assert "知识" not in r["message"] or "通信" in r["message"]
        assert "检索到" not in r["message"]
        assert "调度" not in r["agent"].lower() or r["agent"] == "CasualAgent"
        print(f"[{r['agent']}] {text} → {r['message'][:40]}")

    # 专业问题仍然工作
    r = o.handle("帮我做 3.5GHz 200m 的链路预算")
    assert r["intent"] == "simulate_link" and r["success"]
    print("[ok] professional still works:", r["agent"])

    # HTTP
    for text in ["你好", "你是谁", "随便聊聊"]:
        r = post("/api/chat", {"message": text})
        assert r["intent"] == "casual", (text, r)
        assert "检索到" not in r["message"]
        print("[http]", text, "→", r["message"][:36])

    print("\nCASUAL CHAT TEST OK")


if __name__ == "__main__":
    main()
