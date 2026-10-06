"""通信仿真引擎：链路、波束、干扰、网络与调度。"""
from .beamforming import beam_pattern, multi_user_beam_allocation
from .interference import cochannel_interference, diagnose_from_metrics, interference_scenario
from .link_budget import coverage_curve, link_budget, path_loss_uma
from .network import build_scenario, optimize_power

__all__ = [
    "beam_pattern",
    "multi_user_beam_allocation",
    "cochannel_interference",
    "diagnose_from_metrics",
    "interference_scenario",
    "coverage_curve",
    "link_budget",
    "path_loss_uma",
    "build_scenario",
    "optimize_power",
]
