"""链路预算与信道容量仿真。

实现 3GPP TR 38.901 UMa/NLOS 简化路损模型、SNR、香农容量、
以及基于距离采样的覆盖曲线，供智能体输出可解释的工程结论。
"""
from __future__ import annotations

import math
from typing import Any

# 热噪声功率密度 (dBm/Hz) @ 290K
THERMAL_NOISE_DBM_HZ = -174.0


def path_loss_uma(distance_m: float, carrier_ghz: float, environment: str = "urban") -> float:
    """3GPP TR 38.901 UMa 路损简化式（dB）。

    LOS:  PL = 28.0 + 22*log10(d) + 20*log10(fc)
    NLOS: PL = 13.54 + 39.08*log10(d) + 20*log10(fc) + 0.6*(h_ut-1.5)
    """
    d = max(float(distance_m), 1.0)
    fc = max(float(carrier_ghz), 0.1)
    if environment == "rural":
        # 简化 RMa
        return 20.0 * math.log10(d) + 20.0 * math.log10(fc) + 32.4
    if environment == "indoor":
        return 17.0 * math.log10(d) + 20.0 * math.log10(fc) + 46.4
    # urban 默认 NLOS
    return 13.54 + 39.08 * math.log10(d) + 20.0 * math.log10(fc) + 0.6 * (1.5 - 1.5)


def fspl(distance_m: float, carrier_ghz: float) -> float:
    """自由空间路损（Friis）。"""
    d = max(float(distance_m), 1.0)
    fc = max(float(carrier_ghz), 0.1)
    return 32.45 + 20.0 * math.log10(d) + 20.0 * math.log10(fc)


def thermal_noise_dbm(bandwidth_mhz: float, noise_figure_db: float = 7.0) -> float:
    """带内热噪声功率。"""
    bw_hz = max(float(bandwidth_mhz), 0.1) * 1e6
    return THERMAL_NOISE_DBM_HZ + 10.0 * math.log10(bw_hz) + float(noise_figure_db)


def received_power_dbm(
    distance_m: float,
    carrier_ghz: float,
    tx_power_dbm: float,
    tx_gain_dbi: float = 0.0,
    rx_gain_dbi: float = 0.0,
    environment: str = "urban",
) -> dict[str, Any]:
    """计算接收功率与路损分解。"""
    pl = path_loss_uma(distance_m, carrier_ghz, environment)
    prx = float(tx_power_dbm) + float(tx_gain_dbi) + float(rx_gain_dbi) - pl
    return {
        "distance_m": round(float(distance_m), 2),
        "path_loss_db": round(pl, 2),
        "rx_power_dbm": round(prx, 2),
        "carrier_ghz": float(carrier_ghz),
        "environment": environment,
    }


def link_budget(
    distance_m: float = 200.0,
    carrier_ghz: float = 3.5,
    bandwidth_mhz: float = 100.0,
    tx_power_dbm: float = 46.0,
    tx_gain_dbi: float = 18.0,
    rx_gain_dbi: float = 0.0,
    noise_figure_db: float = 7.0,
    environment: str = "urban",
    interference_dbm: float | None = None,
) -> dict[str, Any]:
    """完整链路预算：路损 → 接收功率 → SNR/SINR → 香农容量。"""
    pl = path_loss_uma(distance_m, carrier_ghz, environment)
    prx = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - pl
    noise = thermal_noise_dbm(bandwidth_mhz, noise_figure_db)

    if interference_dbm is None:
        snr_db = prx - noise
        sinr_db = snr_db
        mode = "SNR"
    else:
        denom = 10 ** (noise / 10) + 10 ** (interference_dbm / 10)
        sinr_db = prx - 10 * math.log10(denom)
        snr_db = prx - noise
        mode = "SINR"

    snr_lin = 10 ** (sinr_db / 10)
    capacity_mbps = bandwidth_mhz * math.log2(1.0 + snr_lin)
    spectral_eff = math.log2(1.0 + snr_lin)

    # 工程经验：SINR < -6dB 基本脱网，>20dB 可跑满高阶调制
    if sinr_db < -6:
        quality = "脱网/不可用"
    elif sinr_db < 0:
        quality = "极差(QPSK 低码率)"
    elif sinr_db < 10:
        quality = "一般(16QAM)"
    elif sinr_db < 20:
        quality = "良好(64QAM)"
    else:
        quality = "优秀(256QAM)"

    return {
        "inputs": {
            "distance_m": distance_m,
            "carrier_ghz": carrier_ghz,
            "bandwidth_mhz": bandwidth_mhz,
            "tx_power_dbm": tx_power_dbm,
            "tx_gain_dbi": tx_gain_dbi,
            "rx_gain_dbi": rx_gain_dbi,
            "noise_figure_db": noise_figure_db,
            "environment": environment,
            "interference_dbm": interference_dbm,
        },
        "path_loss_db": round(pl, 2),
        "rx_power_dbm": round(prx, 2),
        "noise_power_dbm": round(noise, 2),
        f"{mode.lower()}_db": round(sinr_db, 2),
        "snr_db": round(snr_db, 2),
        "capacity_mbps": round(capacity_mbps, 2),
        "spectral_efficiency_bps_hz": round(spectral_eff, 3),
        "link_quality": quality,
        "formula": {
            "path_loss": "PL = 13.54 + 39.08*log10(d) + 20*log10(fc)   [UMa NLOS]",
            "rx_power": "Prx = Ptx + Gtx + Grx - PL",
            "shannon": "C = B * log2(1 + SINR)",
        },
    }


def coverage_curve(
    radius_m: float = 500.0,
    samples: int = 25,
    **kwargs: Any,
) -> dict[str, Any]:
    """沿半径采样，输出覆盖曲线（距离 vs SNR / 吞吐）。"""
    radius = max(float(radius_m), 10.0)
    n = max(int(samples), 5)
    points = []
    for i in range(n):
        d = radius * (i + 1) / n
        lb = link_budget(distance_m=d, **kwargs)
        points.append(
            {
                "distance_m": round(d, 1),
                "snr_db": lb["snr_db"],
                "capacity_mbps": lb["capacity_mbps"],
                "rx_power_dbm": lb["rx_power_dbm"],
                "path_loss_db": lb["path_loss_db"],
            }
        )

    # 有效覆盖边界：SNR >= 0 dB
    edge = None
    for p in points:
        if p["snr_db"] >= 0:
            edge = p["distance_m"]
        else:
            break

    return {
        "radius_m": radius,
        "points": points,
        "coverage_edge_m": edge,
        "summary": (
            f"在 {kwargs.get('carrier_ghz', 3.5)} GHz / {kwargs.get('bandwidth_mhz', 100)} MHz 下，"
            f"SNR≥0dB 的有效覆盖半径约 {edge if edge else '<'+str(points[0]['distance_m'])} m"
        ),
    }
