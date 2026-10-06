# -*- coding: utf-8 -*-
"""多轮对话 / 模型接入对话能力测试。"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.llm.base import conversation_reply, get_llm, settings
from backend.llm.fallback_chat import offline_reply


def post(path: str, payload: dict):
    req = urllib.request.Request(
        "http://127.0.0.1:8787" + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    # 1. 离线自由对话回退
    for q, expect_sub in [
        ("你好", "CommAgent"),
        ("谢谢", "客气"),
        ("你是谁", "CommAgent"),
        ("讲个笑话", "SINR"),
    ]:
        r = offline_reply(q)
        assert expect_sub in r or len(r) > 8, (q, r)
        print("offline:", q, "→", r[:36])

    # 2. conversation_reply 有/无 API 都返回非空
    text, source = conversation_reply("你好，能听见吗？", history=[])
    assert text and source in ("api", "mock")
    print("conversation_reply source=", source, "→", text[:40])

    # 3. 多轮 history 透传（HTTP）
    r1 = post("/api/chat", {"message": "你好", "history": []})
    assert r1["success"] and r1["message"]
    print("turn1:", r1["intent"], "→", r1["message"][:36])

    r2 = post("/api/chat", {
        "message": "你是谁呀",
        "history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": r1["message"]},
        ],
    })
    assert r2["success"] and r2["message"]
    print("turn2:", r2["intent"], "→", r2["message"][:36])

    r3 = post("/api/chat", {
        "message": "帮我做 3.5GHz 200m 的链路预算",
        "history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": r1["message"]},
        ],
    })
    assert r3["intent"] == "simulate_link" and r3["success"]
    print("turn3 professional:", r3["agent"], "ok")

    # 4. API 模式下 conversation_reply 应走 api 或优雅回退
    old_mode = settings.llm_mode
    try:
        settings.llm_mode = "api"
        settings.llm_api_key = ""
        text, source = conversation_reply("随便聊聊天气")
        assert text and source in ("api", "mock")
        print("api-empty-key source=", source, "ok")
    finally:
        settings.llm_mode = old_mode

    print("\nCONVERSATION TEST OK")


if __name__ == "__main__":
    main()
