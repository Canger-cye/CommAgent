# -*- coding: utf-8 -*-
"""HTTP API 集成测试（UTF-8 安全）。"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

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
    h = get("/api/health")
    print("health:", h["status"], h["llm_mode"], h["llm_class"])

    r = post("/api/chat", {"message": "帮我做 3.5GHz 100MHz、距离 200m 的链路预算"})
    print("chat1:", r["intent"], r["agent"], "snr=", r["data"]["link_budget"]["snr_db"])

    r = post("/api/chat", {"message": "SINR 是 -2dB，BLER 0.12，帮我做根因诊断"})
    print("chat2:", r["intent"], r["agent"], "overall=", r["data"]["overall"])

    r = post("/api/chat", {"message": "3 个基站 20 个用户组网，优化功率提升吞吐"})
    print("chat3:", r["intent"], r["agent"])
    print("       ", r["message"][:140])

    r = post("/api/chat", {"message": "生成一份网络仿真与诊断报告"})
    print("chat4:", r["intent"], r["agent"], "keys=", list(r["data"].keys()))
    report = r["data"].get("report") or {}
    print("       report sections=", len(report.get("sections", [])), "msg=", r["message"][:80])

    sc = get("/api/scenario?n_bs=3&n_ue=20&seed=42")
    print("scenario stats:", sc["stats"])

    opt = post("/api/optimize", {"n_bs": 3, "n_ue": 20, "seed": 42, "area_m": 1200,
                                 "carrier_ghz": 3.5, "bandwidth_mhz": 100,
                                 "tx_power_dbm": 46, "environment": "urban"})
    print("optimize before:", opt["before"].get("avg_capacity_mbps"),
          "after:", opt["after"]["avg_capacity_mbps"],
          "delta:", opt["delta_capacity_mbps"])
    print("actions:", [(a["bs_id"], a["action"], a["from_dbm"], a["to_dbm"]) for a in opt["actions"]])

    idx = urllib.request.urlopen(BASE + "/", timeout=10)
    html = idx.read().decode("utf-8", errors="replace")
    print("index.html bytes:", len(html), "has CommAgent:", "CommAgent" in html)

    print("HTTP INTEGRATION OK")


if __name__ == "__main__":
    main()
