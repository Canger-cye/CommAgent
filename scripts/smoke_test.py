# -*- coding: utf-8 -*-
"""CommAgent 冒烟测试：意图分类 + 编排器全链路。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.agents import Orchestrator
from backend.llm.base import classify_intent


def main() -> None:
    tests = [
        "帮我做 3.5GHz 100MHz、距离 200m 的链路预算",
        "帮我做 3.5GHz 100MHz 带宽、距离 200m 的链路预算和覆盖曲线",
        "SINR 是 -2dB，BLER 0.12，帮我做根因诊断",
        "分析 16 阵元波束赋形方向图和多用户波束分配",
        "服务距离 150m，2 个同频干扰源，分析 SINR",
        "3 个基站 20 个用户组网，优化功率提升吞吐",
        "生成一份网络仿真与诊断报告",
        "什么是香农公式和它的工程意义？",
    ]
    print("=== intent classification ===")
    expected = [
        "simulate_link",
        "simulate_link",
        "diagnose",
        "simulate_beam",
        "simulate_interference",
        "optimize",
        "report",
        "knowledge",
    ]
    ok = 0
    for t, exp in zip(tests, expected):
        r = classify_intent(t)
        mark = "OK" if r["intent"] == exp else f"MISS(exp={exp})"
        if r["intent"] == exp:
            ok += 1
        print(f"[{mark}] {r['intent']:22s} conf={r['confidence']} ent={r['entities']}")
        print(f"       {t}")

    print(f"\nintent accuracy: {ok}/{len(tests)}")

    print("\n=== orchestrator smoke ===")
    o = Orchestrator()
    for t in [tests[0], tests[2], tests[5], tests[6]]:
        r = o.handle(t)
        status = "OK" if r["success"] else "FAIL"
        print(f"[{status}] intent={r['intent']} agent={r['agent']}")
        print(f"       {r['message'][:120].replace(chr(10), ' ')}")

    print("\nALL DONE")


if __name__ == "__main__":
    main()
