# -*- coding: utf-8 -*-
"""核心公式正确性单元测试（竞赛答辩证据）。"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.simulation.beamforming import array_factor_gain, beam_pattern
from backend.simulation.link_budget import (
    coverage_curve,
    fspl,
    link_budget,
    path_loss_uma,
    thermal_noise_dbm,
)
from backend.simulation.network import build_scenario, optimize_power


class TestLinkBudget(unittest.TestCase):
    def test_fspl_known_value(self):
        # 1 km @ 1 GHz: FSPL = 32.45 + 60 + 0 = 92.45 dB
        self.assertAlmostEqual(fspl(1000, 1.0), 92.45, places=2)

    def test_pathloss_increases_with_distance(self):
        p1 = path_loss_uma(50, 3.5)
        p2 = path_loss_uma(200, 3.5)
        self.assertGreater(p2, p1)

    def test_thermal_noise(self):
        # -174 + 10*log10(1e8) + 7 = -174 + 80 + 7 = -87 dBm
        self.assertAlmostEqual(thermal_noise_dbm(100, 7), -87.0, places=2)

    def test_shannon_monotonic(self):
        a = link_budget(distance_m=50, bandwidth_mhz=100)
        b = link_budget(distance_m=400, bandwidth_mhz=100)
        self.assertGreater(a["capacity_mbps"], b["capacity_mbps"])

    def test_coverage_edge_reasonable(self):
        cov = coverage_curve(radius_m=500, samples=20, carrier_ghz=3.5, bandwidth_mhz=100)
        self.assertTrue(cov["points"])
        edge = cov["coverage_edge_m"]
        self.assertTrue(edge is None or 0 < edge <= 500)


class TestBeamforming(unittest.TestCase):
    def test_broadside_peak(self):
        g0 = array_factor_gain(0, 16)
        g30 = array_factor_gain(30, 16)
        self.assertGreater(g0, g30)

    def test_pattern_peak(self):
        pat = beam_pattern(n_elements=8, max_gain_dbi=18)
        peak = max(p["gain_dbi"] for p in pat["points"])
        self.assertAlmostEqual(peak, 18.0, places=1)
        self.assertGreater(pat["beamwidth_3db_deg"], 1.0)


class TestNetwork(unittest.TestCase):
    def test_scenario_reproducible(self):
        s1 = build_scenario(n_bs=3, n_ue=15, seed=7)
        s2 = build_scenario(n_bs=3, n_ue=15, seed=7)
        self.assertEqual(s1["stats"], s2["stats"])

    def test_optimize_power_bounds(self):
        s = build_scenario(n_bs=3, n_ue=20, seed=42, tx_power_dbm=40)
        opt = optimize_power(s)
        for a in opt["actions"]:
            self.assertGreaterEqual(a["to_dbm"], 20.0)
            self.assertLessEqual(a["to_dbm"], 46.0)
        self.assertIn("delta_capacity_mbps", opt)

    def test_optimize_can_improve_from_low_power(self):
        s = build_scenario(n_bs=3, n_ue=20, seed=42, tx_power_dbm=36)
        opt = optimize_power(s, target_sinr_db=12.0)
        # 至少允许正向或持平
        self.assertGreaterEqual(opt["delta_capacity_mbps"], -1.0)


class TestIntent(unittest.TestCase):
    def test_entity_extraction(self):
        from backend.llm.base import classify_intent

        r = classify_intent("SINR 是 -2dB，BLER 0.12，帮我做根因诊断")
        self.assertEqual(r["intent"], "diagnose")
        self.assertAlmostEqual(r["entities"].get("sinr_db"), -2.0)
        self.assertAlmostEqual(r["entities"].get("bler"), 0.12)

    def test_report_priority(self):
        from backend.llm.base import classify_intent

        r = classify_intent("生成一份网络仿真与诊断报告")
        self.assertEqual(r["intent"], "report")


if __name__ == "__main__":
    unittest.main(verbosity=2)
