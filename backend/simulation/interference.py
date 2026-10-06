"""干扰分析与根因诊断仿真。"""
from __future__ import annotations

import math
from typing import Any

from .link_budget import link_budget, path_loss_uma, thermal_noise_dbm


def cochannel_interference(
    serving_distance_m: float,
    interferer_distances_m: list[float],
    carrier_ghz: float = 3.5,
    tx_power_dbm: float = 46.0,
    bandwidth_mhz: float = 100.0,
    noise_figure_db: float = 7.0,
    environment: str = "urban",
    tx_gain_dbi: float = 18.0,
    rx_gain_dbi: float = 0.0,
) -> dict[str, Any]:
    """同频干扰下 SINR 计算。"""
    pl_s = path_loss_uma(serving_distance_m, carrier_ghz, environment)
    prx_s = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - pl_s

    i_total_mw = 0.0
    interferers = []
    for d in interferer_distances_m:
        pl_i = path_loss_uma(d, carrier_ghz, environment)
        prx_i = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - pl_i
        i_mw = 10 ** (prx_i / 10)
        i_total_mw += i_mw
        interferers.append(
            {
                "distance_m": d,
                "rx_power_dbm": round(prx_i, 2),
                "path_loss_db": round(pl_i, 2),
            }
        )

    noise_dbm = thermal_noise_dbm(bandwidth_mhz, noise_figure_db)
    i_dbm = 10 * math.log10(i_total_mw) if i_total_mw > 0 else -200.0
    denom_mw = 10 ** (noise_dbm / 10) + i_total_mw
    sinr_db = prx_s - 10 * math.log10(denom_mw)

    # 判定主干扰源
    main = max(interferers, key=lambda x: x["rx_power_dbm"]) if interferers else None

    return {
        "serving": {"distance_m": serving_distance_m, "rx_power_dbm": round(prx_s, 2)},
        "interferers": interferers,
        "interference_dbm": round(i_dbm, 2) if i_total_mw > 0 else None,
        "noise_dbm": round(noise_dbm, 2),
        "sinr_db": round(sinr_db, 2),
        "main_interferer": main,
        "summary": (
            f"服务小区 d={serving_distance_m}m，{len(interferers)} 个同频干扰源，"
            f"SINR={sinr_db:.1f} dB"
            + (f"，主干扰源在 {main['distance_m']} m" if main else "")
        ),
    }


def diagnose_from_metrics(
    sinr_db: float | None = None,
    throughput_mbps: float | None = None,
    bler: float | None = None,
    rsrp_dbm: float | None = None,
    interference_dbm: float | None = None,
    prb_utilization: float | None = None,
    distance_m: float | None = None,
) -> dict[str, Any]:
    """基于 KPI 的规则根因诊断，返回可解释结论与建议。"""
    findings: list[dict[str, Any]] = []

    if sinr_db is not None and sinr_db < 0:
        findings.append(
            {
                "level": "critical",
                "signal": "SINR",
                "value": f"{sinr_db} dB",
                "reason": "SINR 低于 0 dB，链路处于噪声/干扰受限，高阶调制无法工作。",
                "suggestion": "检查同频邻区、增大下倾角/降低导频功率、开启干扰协调 ICIC 或波束赋形窄波束。",
            }
        )
    elif sinr_db is not None and sinr_db < 10:
        findings.append(
            {
                "level": "warning",
                "signal": "SINR",
                "value": f"{sinr_db} dB",
                "reason": "SINR 偏低，吞吐会被迫回落到 16QAM 以下。",
                "suggestion": "优化邻区关系或调整波束指向，目标 SINR ≥ 15 dB。",
            }
        )

    if rsrp_dbm is not None and rsrp_dbm < -110:
        findings.append(
            {
                "level": "critical",
                "signal": "RSRP",
                "value": f"{rsrp_dbm} dBm",
                "reason": "参考信号接收功率过弱，覆盖受限。",
                "suggestion": "增加载波功率/天线增益，补盲点，或降低小区半径。",
            }
        )

    if interference_dbm is not None and sinr_db is not None:
        noise_like = -100.0
        if interference_dbm > noise_like + 10:
            findings.append(
                {
                    "level": "critical",
                    "signal": "I",
                    "value": f"{interference_dbm} dBm",
                    "reason": "干扰功率显著高于热噪声，属干扰受限网络。",
                    "suggestion": "频率复用加严、波束隔离、功率回退或启用 eICIC。",
                }
            )

    if bler is not None and bler > 0.1:
        findings.append(
            {
                "level": "warning",
                "signal": "BLER",
                "value": f"{bler}",
                "reason": "误块率过高，HARQ 重传拉低有效吞吐。",
                "suggestion": "降低 MCS 等级、增强编码、排除上行干扰。",
            }
        )

    if prb_utilization is not None and prb_utilization > 0.9:
        findings.append(
            {
                "level": "warning",
                "signal": "PRB",
                "value": f"{prb_utilization}",
                "reason": "资源利用率接近饱和，小区负载过高。",
                "suggestion": "负载均衡、扩容载波或分流到邻区。",
            }
        )

    if distance_m is not None and distance_m > 400:
        findings.append(
            {
                "level": "info",
                "signal": "d",
                "value": f"{distance_m} m",
                "reason": "UE 距离基站较远，边缘用户体验下降。",
                "suggestion": "检查覆盖边缘是否需要小型站或中继。",
            }
        )

    if not findings:
        findings.append(
            {
                "level": "ok",
                "signal": "ALL",
                "value": "正常",
                "reason": "当前 KPI 均在健康区间。",
                "suggestion": "保持现状，持续监控。",
            }
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
    findings.sort(key=lambda x: severity_order.get(x["level"], 9))
    overall = findings[0]["level"]

    return {
        "overall": overall,
        "findings": findings,
        "summary": f"诊断完成：{len(findings)} 条结论，整体等级 {overall}",
    }


def interference_scenario(
    n_interferers: int = 2,
    serving_distance_m: float = 150.0,
    interferer_distances_m: list[float] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """快速干扰场景：默认等距干扰源。"""
    if interferer_distances_m is None:
        interferer_distances_m = [250.0 + i * 80.0 for i in range(max(n_interferers, 0))]
    result = cochannel_interference(
        serving_distance_m=serving_distance_m,
        interferer_distances_m=interferer_distances_m,
        **kwargs,
    )
    # 补上容量
    lb = link_budget(
        distance_m=serving_distance_m,
        interference_dbm=result["interference_dbm"] if result["interference_dbm"] is not None else -200,
        **{k: v for k, v in kwargs.items() if k in (
            "carrier_ghz", "bandwidth_mhz", "tx_power_dbm", "tx_gain_dbi",
            "rx_gain_dbi", "noise_figure_db", "environment",
        )},
    )
    result["capacity_mbps"] = lb["capacity_mbps"]
    result["link_quality"] = lb["link_quality"]
    return result
