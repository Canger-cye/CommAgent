# -*- coding: utf-8 -*-
"""模型设置 API 测试。"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BASE = "http://127.0.0.1:8787"


def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    # 1. 读配置
    cfg = get("/api/llm/config")
    print("config mode=", cfg["llm_mode"], "model=", cfg["llm_model"], "key_set=", cfg.get("llm_api_key_set"))
    assert cfg["llm_mode"] in ("mock", "api")

    # 2. 预设
    pre = get("/api/llm/presets")
    print("presets:", [p["id"] for p in pre["presets"]])
    assert len(pre["presets"]) >= 5

    # 3. 测试 mock 连接
    t = post("/api/llm/test", {"llm_mode": "mock", "llm_model": "", "llm_api_base": ""})
    print("test mock:", t["ok"], t["detail"][:40])
    assert t["ok"]

    # 4. 切换到 api 模式再切回
    r = post("/api/llm/config", {
        "llm_mode": "api",
        "llm_model": "deepseek-chat",
        "llm_api_base": "https://api.deepseek.com/v1",
        "llm_api_key": "sk-test-not-real",
        "llm_timeout": 15,
        "llm_temperature": 0.2,
    })
    print("save api mode:", r["ok"], r["config"]["llm_model"], r["config"]["llm_mode"])
    assert r["config"]["llm_mode"] == "api"
    assert r["config"]["llm_api_key_set"] is True
    assert "test" in r["config"]["llm_api_key"] or "…" in r["config"]["llm_api_key"]

    # 5. health 应反映新模型
    h = get("/api/health")
    print("health after switch:", h["llm_mode"], h["llm_model"], h["llm_class"])
    assert h["llm_mode"] == "api"

    # 6. 切回 mock
    r = post("/api/llm/config", {
        "llm_mode": "mock",
        "llm_model": "builtin-rules",
        "llm_api_base": "",
        "llm_timeout": 30,
        "llm_temperature": 0.3,
    })
    h = get("/api/health")
    print("health back:", h["llm_mode"], h["llm_class"])
    assert h["llm_mode"] == "mock"

    # 7. 前端资源
    html = urllib.request.urlopen(BASE + "/", timeout=10).read().decode("utf-8")
    assert "模型设置" in html and "drawer" in html
    css = urllib.request.urlopen(BASE + "/static/style.css", timeout=10).read().decode("utf-8")
    assert "drawer" in css and "--accent" in css
    js = urllib.request.urlopen(BASE + "/static/app.js", timeout=10).read().decode("utf-8")
    assert "api/llm/config" in js and "presetGrid" in js
    print("frontend assets ok: html", len(html), "css", len(css), "js", len(js))

    print("LLM CONFIG API OK")


if __name__ == "__main__":
    main()
