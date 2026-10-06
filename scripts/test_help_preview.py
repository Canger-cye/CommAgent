# -*- coding: utf-8 -*-
"""帮助意图 + 抽屉/预览资源回归测试。"""
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


def main() -> None:
    # 1. 帮助意图
    r = post("/api/chat", {"message": "给我几个可以问的问题"})
    print("help intent:", r["intent"], r["agent"])
    assert r["intent"] == "help", r["intent"]
    assert r["agent"] == "HelpAgent"
    assert "链路预算" in r["message"] or "链路" in r["message"]
    assert "检索到" not in r["message"]
    print("  msg head:", r["message"][:60].replace("\n", " | "))

    # 2. 知识问答仍正常，但格式更自然
    r2 = post("/api/chat", {"message": "什么是香农公式？"})
    print("knowledge:", r2["intent"], r2["agent"])
    assert r2["intent"] == "knowledge"
    assert "香农" in r2["message"]
    assert not r2["message"].startswith("检索到")

    # 3. 帮助里不要混进知识库长文
    r3 = post("/api/chat", {"message": "怎么使用这个系统"})
    print("usage help:", r3["intent"], r3["agent"], "len", len(r3["message"]))
    assert r3["intent"] == "help"
    assert len(r3["message"]) < 800

    # 4. 前端资源：抽屉不遮挡相关样式 + 相对路径 + 预览 mock
    html = urllib.request.urlopen(BASE + "/", timeout=10).read().decode("utf-8")
    assert 'href="static/style.css"' in html and 'src="static/app.js"' in html
    css = urllib.request.urlopen(BASE + "/static/style.css", timeout=10).read().decode("utf-8")
    assert "drawer-open" in css and "padding-right" in css
    js = urllib.request.urlopen(BASE + "/static/app.js", timeout=10).read().decode("utf-8")
    assert "mockHandle" in js and "HelpAgent" in js
    print("assets ok")

    # 5. 工作目录入口文件
    cwd = Path(__file__).resolve().parents[1].parent
    assert (cwd / "index.html").exists(), "cwd/index.html missing"
    assert (cwd / "static" / "style.css").exists()
    assert (cwd / "static" / "app.js").exists()
    print("cwd entry ok:", cwd / "index.html")

    print("HELP + PREVIEW TEST OK")


if __name__ == "__main__":
    main()
