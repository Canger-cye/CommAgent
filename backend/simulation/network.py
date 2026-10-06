"""网络场景：基站/UE 拓扑、覆盖热力、KPI 汇总。"""
from __future__ import annotations

import math
import random
from typing import Any

from .link_budget import link_budget, path_loss_uma


def build_scenario(
    n_bs: int = 3,
    n_ue: int = 20,
    area_m: float = 1200.0,
    seed: int = 42,
    carrier_ghz: float = 3.5,
    bandwidth_mhz: float = 100.0,
    tx_power_dbm: float = 46.0,
    environment: str = "urban",
) -> dict[str, Any]:
    """生成可复现的蜂窝拓扑（六边形近似 + 随机 UE）。"""
    rng = random.Random(seed)
    base_stations = []
    # 中心 + 环上均匀
    if n_bs >= 1:
        base_stations.append({"id": "BS-1", "x": 0.0, "y": 0.0, "tx_power_dbm": tx_power_dbm})
    ring = max(n_bs - 1, 0)
    if ring > 0:
        radius = area_m / 3.0
        for i in range(ring):
            ang = 2 * math.pi * i / ring
            base_stations.append(
                {
                    "id": f"BS-{i+2}",
                    "x": round(radius * math.cos(ang), 1),
                    "y": round(radius * math.sin(ang), 1),
                    "tx_power_dbm": tx_power_dbm,
                }
            )

    users = []
    for i in range(n_ue):
        x = rng.uniform(-area_m / 2, area_m / 2)
        y = rng.uniform(-area_m / 2, area_m / 2)
        users.append({"id": f"UE-{i+1}", "x": round(x, 1), "y": round(y, 1)})

    # 关联：最近基站
    kpis = []
    for u in users:
        best_bs = None
        best_d = 1e18
        for bs in base_stations:
            d = math.hypot(u["x"] - bs["x"], u["y"] - bs["y"])
            if d < best_d:
                best_d = d
                best_bs = bs
        # 干扰：其余基站
        i_mw = 0.0
        for bs in base_stations:
            if bs["id"] == best_bs["id"]:
                continue
            d = math.hypot(u["x"] - bs["x"], u["y"] - bs["y"])
            prx = bs["tx_power_dbm"] + 18.0 - path_loss_uma(d, carrier_ghz, environment)
            i_mw += 10 ** (prx / 10)
        interf = 10 * math.log10(i_mw) if i_mw > 0 else -200.0

        lb = link_budget(
            distance_m=max(best_d, 1.0),
            carrier_ghz=carrier_ghz,
            bandwidth_mhz=bandwidth_mhz,
            tx_power_dbm=best_bs["tx_power_dbm"],
            tx_gain_dbi=18.0,
            rx_gain_dbi=0.0,
            noise_figure_db=7.0,
            environment=environment,
            interference_dbm=interf if i_mw > 0 else None,
        )
        kpis.append(
            {
                "ue_id": u["id"],
                "x": u["x"],
                "y": u["y"],
                "serving_bs": best_bs["id"],
                "distance_m": round(best_d, 1),
                "snr_db": lb["snr_db"],
                "sinr_db": lb.get("sinr_db", lb["snr_db"]),
                "capacity_mbps": lb["capacity_mbps"],
                "rx_power_dbm": lb["rx_power_dbm"],
                "link_quality": lb["link_quality"],
            }
        )

    sinrs = [k["sinr_db"] for k in kpis]
    caps = [k["capacity_mbps"] for k in kpis]
    return {
        "params": {
            "n_bs": n_bs,
            "n_ue": n_ue,
            "area_m": area_m,
            "seed": seed,
            "carrier_ghz": carrier_ghz,
            "bandwidth_mhz": bandwidth_mhz,
            "tx_power_dbm": tx_power_dbm,
            "environment": environment,
        },
        "base_stations": base_stations,
        "users": users,
        "kpis": kpis,
        "stats": {
            "avg_sinr_db": round(sum(sinrs) / len(sinrs), 2) if sinrs else 0,
            "min_sinr_db": round(min(sinrs), 2) if sinrs else 0,
            "avg_capacity_mbps": round(sum(caps) / len(caps), 2) if caps else 0,
            "cell_edge_sinr_db": round(sorted(sinrs)[max(int(len(sinrs) * 0.05) - 1, 0)], 2) if sinrs else 0,
            "weak_ue_count": sum(1 for k in kpis if k["sinr_db"] < 5),
        },
    }


def _kpi_with_powers(
    template_scenario: dict[str, Any],
    powers: dict[str, float],
) -> dict[str, Any]:
    """按给定功率重算场景 KPI（口径与 build_scenario 一致：含同频干扰）。"""
    import copy

    scenario = copy.deepcopy(template_scenario)
    for bs in scenario["base_stations"]:
        if bs["id"] in powers:
            bs["tx_power_dbm"] = powers[bs["id"]]

    carrier = scenario["params"]["carrier_ghz"]
    env = scenario["params"]["environment"]
    for k in scenario["kpis"]:
        best_bs = next(b for b in scenario["base_stations"] if b["id"] == k["serving_bs"])
        i_mw = 0.0
        for bs in scenario["base_stations"]:
            if bs["id"] == best_bs["id"]:
                continue
            d = ((k["x"] - bs["x"]) ** 2 + (k["y"] - bs["y"]) ** 2) ** 0.5
            prx_i = bs["tx_power_dbm"] + 18.0 - path_loss_uma(d, carrier, env)
            i_mw += 10 ** (prx_i / 10)
        interf = 10 * math.log10(i_mw) if i_mw > 0 else -200.0
        lb = link_budget(
            distance_m=k["distance_m"],
            carrier_ghz=carrier,
            bandwidth_mhz=scenario["params"]["bandwidth_mhz"],
            tx_power_dbm=best_bs["tx_power_dbm"],
            environment=env,
            interference_dbm=interf if i_mw > 0 else None,
        )
        k["snr_db"] = lb["snr_db"]
        k["sinr_db"] = lb.get("sinr_db", lb["snr_db"])
        k["capacity_mbps"] = lb["capacity_mbps"]

    caps = [k["capacity_mbps"] for k in scenario["kpis"]]
    sinrs = [k["sinr_db"] for k in scenario["kpis"]]
    scenario["stats"] = {
        "avg_sinr_db": round(sum(sinrs) / len(sinrs), 2) if sinrs else 0,
        "min_sinr_db": round(min(sinrs), 2) if sinrs else 0,
        "avg_capacity_mbps": round(sum(caps) / len(caps), 2) if caps else 0,
        "cell_edge_sinr_db": round(sorted(sinrs)[max(int(len(sinrs) * 0.05) - 1, 0)], 2) if sinrs else 0,
        "weak_ue_count": sum(1 for k in scenario["kpis"] if k["sinr_db"] < 5),
    }
    return scenario


def optimize_power(
    scenario: dict[str, Any],
    target_sinr_db: float = 15.0,
    max_power_dbm: float = 46.0,
    min_power_dbm: float = 20.0,
) -> dict[str, Any]:
    """功率优化：干扰受限网络下用局部搜索最大化平均吞吐。

    均匀抬功率在干扰受限时无效甚至有害，因此对每基站功率做
    {-2, 0, +2} dB 局部搜索，保留使平均容量最大的组合。
    """
    base_stations = scenario.get("base_stations", [])
    if not base_stations or not scenario.get("kpis"):
        return {"message": "场景为空", "actions": []}

    cur_powers = {bs["id"]: float(bs.get("tx_power_dbm", max_power_dbm)) for bs in base_stations}
    bs_ids = list(cur_powers.keys())

    # 规则建议（用于解释）
    agg: dict[str, list[float]] = {}
    for k in scenario["kpis"]:
        agg.setdefault(k["serving_bs"], []).append(k["sinr_db"])

    def clamp(p: float) -> float:
        return max(min_power_dbm, min(max_power_dbm, p))

    # 候选：对每个基站尝试 -2/0/+2
    best_powers = dict(cur_powers)
    best_scen = _kpi_with_powers(scenario, best_powers)
    best_cap = best_scen["stats"]["avg_capacity_mbps"]

    for bs_id in bs_ids:
        local_best_p = best_powers[bs_id]
        local_best_cap = best_cap
        for delta in (-2.0, 0.0, 2.0):
            trial = dict(best_powers)
            trial[bs_id] = clamp(cur_powers[bs_id] + delta)
            scen = _kpi_with_powers(scenario, trial)
            cap = scen["stats"]["avg_capacity_mbps"]
            if cap > local_best_cap + 1e-6:
                local_best_cap = cap
                local_best_p = trial[bs_id]
        if local_best_p != best_powers[bs_id]:
            best_powers[bs_id] = local_best_p
            best_cap = local_best_cap

    # 二轮联合微调
    improved = True
    rounds = 0
    while improved and rounds < 3:
        improved = False
        rounds += 1
        for bs_id in bs_ids:
            for delta in (-2.0, 2.0):
                trial = dict(best_powers)
                trial[bs_id] = clamp(best_powers[bs_id] + delta)
                if trial[bs_id] == best_powers[bs_id]:
                    continue
                scen = _kpi_with_powers(scenario, trial)
                cap = scen["stats"]["avg_capacity_mbps"]
                if cap > best_cap + 1e-6:
                    best_cap = cap
                    best_powers = trial
                    improved = True

    new_scenario = _kpi_with_powers(scenario, best_powers)

    actions = []
    for bs_id in bs_ids:
        cur = cur_powers[bs_id]
        new_p = best_powers[bs_id]
        avg = sum(agg.get(bs_id, [0])) / max(len(agg.get(bs_id, [1])), 1)
        if new_p > cur:
            act, why = "increase_power", f"局部搜索表明 +{new_p-cur:.0f} dB 可提升系统平均吞吐（该小区平均 SINR {avg:.1f} dB）。"
        elif new_p < cur:
            act, why = "reduce_power", f"回退 {cur-new_p:.0f} dB 以降低对邻区干扰（该小区平均 SINR {avg:.1f} dB）。"
        else:
            act, why = "keep", f"当前功率已局部最优（该小区平均 SINR {avg:.1f} dB）。"
        actions.append(
            {
                "bs_id": bs_id,
                "action": act,
                "from_dbm": cur,
                "to_dbm": new_p,
                "reason": why,
            }
        )

    before = scenario.get("stats", {})
    after = new_scenario["stats"]
    delta = round(after["avg_capacity_mbps"] - before.get("avg_capacity_mbps", 0), 2)

    return {
        "actions": actions,
        "before": before,
        "after": after,
        "delta_capacity_mbps": delta,
        "scenario_after": new_scenario,
        "summary": (
            f"功率局部搜索完成（{rounds} 轮），平均吞吐变化 {delta:+.2f} Mbps，"
            f"共 {len(actions)} 条调整动作。"
        ),
    }
