"""波束赋形与天线方向图仿真（3GPP 简化模型）。"""
from __future__ import annotations

import math
from typing import Any


def array_factor_gain(theta_deg: float, n_elements: int, spacing_lambda: float = 0.5) -> float:
    """均匀线阵(ULA)归一化阵列因子（dB），峰值 0 dB @ 波束轴。

    AF = |sin(Nπd sinθ) / (N sin(πd sinθ))|，峰值为 1。
    theta 为相对波束轴夹角。
    """
    n = max(int(n_elements), 1)
    theta = math.radians(float(theta_deg))
    arg = math.pi * spacing_lambda * math.sin(theta)
    if abs(math.sin(arg)) < 1e-12:
        return 0.0  # 归一化峰值
    af = abs(math.sin(n * arg) / (n * math.sin(arg)))
    af = max(af, 1e-6)
    return 20.0 * math.log10(af)


def element_pattern_gain(theta_deg: float, max_gain_dbi: float = 8.0, beamwidth_3db_deg: float = 65.0) -> float:
    """单阵元水平方向图（3GPP 简化）。"""
    theta = float(theta_deg)
    # 归一化到 ±180
    theta = ((theta + 180.0) % 360.0) - 180.0
    half = beamwidth_3db_deg / 2.0
    if abs(theta) <= half:
        return max_gain_dbi - 3.0 * (abs(theta) / half) ** 2
    # 主瓣外快速衰减，下限 -20 dB
    excess = abs(theta) - half
    return max(-20.0, max_gain_dbi - 3.0 - excess * 0.25)


def beam_pattern(
    n_elements: int = 8,
    max_gain_dbi: float = 18.0,
    beamwidth_3db_deg: float = 65.0,
    tilt_deg: float = 0.0,
    samples: int = 181,
) -> dict[str, Any]:
    """生成水平面方向图采样，用于前端极坐标/直角坐标绘制。

    合成方式：total = 单元方向图 + 相对阵列因子（峰值 0 dB），
    再平移使峰值等于 max_gain_dbi，避免绝对增益重复叠加。
    """
    n = max(int(n_elements), 1)
    points = []
    peak = -999.0
    for i in range(samples):
        az = -180.0 + 360.0 * i / (samples - 1)
        rel = az - tilt_deg
        af_rel = array_factor_gain(rel, n)  # 已归一化，峰值 0 dB
        el = element_pattern_gain(rel, max_gain_dbi=max_gain_dbi, beamwidth_3db_deg=beamwidth_3db_deg)
        total = el + af_rel
        # 显示限幅：零陷不要出现 -100 dB 级离谱值
        total = max(total, -40.0)
        points.append({"azimuth_deg": round(az, 1), "gain_dbi": round(total, 2)})
        peak = max(peak, total)

    offset = max_gain_dbi - peak
    for p in points:
        p["gain_dbi"] = round(p["gain_dbi"] + offset, 2)

    bw3 = _beamwidth_3db(points, tilt_deg)

    return {
        "n_elements": n_elements,
        "max_gain_dbi": max_gain_dbi,
        "tilt_deg": tilt_deg,
        "beamwidth_3db_deg": round(bw3, 1),
        "points": points,
        "summary": (
            f"{n_elements} 阵元 ULA，峰值增益 {max_gain_dbi} dBi，"
            f"3dB 波束宽度约 {bw3:.1f}°，电下倾 {tilt_deg}°"
        ),
    }


def _beamwidth_3db(points: list[dict], tilt_deg: float) -> float:
    peak = max(p["gain_dbi"] for p in points)
    threshold = peak - 3.0
    above = [p["azimuth_deg"] for p in points if p["gain_dbi"] >= threshold]
    if not above:
        return 360.0
    # 取包含 tilt 的连通段宽度
    # 简化：最大间隔
    above_sorted = sorted(above)
    # 找与 tilt 最近的段
    diffs = [abs(a - tilt_deg) for a in above_sorted]
    idx = diffs.index(min(diffs))
    left = above_sorted[idx]
    right = above_sorted[idx]
    i = idx
    while i > 0 and above_sorted[i] - above_sorted[i - 1] < 30:
        i -= 1
        left = above_sorted[i]
    j = idx
    while j < len(above_sorted) - 1 and above_sorted[j + 1] - above_sorted[j] < 30:
        j += 1
        right = above_sorted[j]
    return max(right - left, 1.0)


def multi_user_beam_allocation(
    n_users: int = 4,
    sector_deg: float = 120.0,
    n_elements: int = 16,
    max_gain_dbi: float = 24.0,
) -> dict[str, Any]:
    """多用户等角波束分配 + 理想 ZF 后的每用户增益估计。"""
    n = max(int(n_users), 1)
    beams = []
    start = -sector_deg / 2.0
    step = sector_deg / n
    for i in range(n):
        az = start + step * (i + 0.5)
        # 理想窄波束：峰值增益按 10*log10(N) 简化
        gain = 10.0 * math.log10(n_elements) + 10.0 * math.log10(n) * 0.15
        beams.append(
            {
                "user_id": i + 1,
                "azimuth_deg": round(az, 1),
                "beam_gain_dbi": round(min(gain, max_gain_dbi), 2),
            }
        )
    return {
        "n_users": n,
        "n_elements": n_elements,
        "sector_deg": sector_deg,
        "beams": beams,
        "total_array_gain_dbi": round(10.0 * math.log10(n_elements), 2),
        "summary": f"{n_elements} 阵元为 {n} 用户分配 {n} 个波束，扇区 {sector_deg}°，等角间隔 {step:.1f}°",
    }
