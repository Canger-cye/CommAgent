# -*- coding: utf-8 -*-
"""扫描仓库中疑似密钥内容。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP = {"dist", "build", "release", "__pycache__", ".git", "node_modules"}
PAT = re.compile(r"sk-[A-Za-z0-9]{8,}|api[_-]?key\s*=\s*['\"][^'\"]{8,}", re.I)
EXT = {".py", ".js", ".json", ".md", ".txt", ".html", ".bat", ".yml", ".yaml", ".env"}

hits = 0
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(x in p.parts for x in SKIP):
        continue
    if p.suffix.lower() not in EXT:
        continue
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    m = PAT.search(t)
    if m:
        print("HIT", p.relative_to(ROOT), "=>", m.group(0)[:30])
        hits += 1

print("scan done, hits =", hits)
