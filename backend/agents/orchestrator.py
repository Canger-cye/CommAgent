"""智能体定义与多智能体编排器。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from ..knowledge import search_knowledge
from ..llm import classify_intent, conversation_reply, get_llm
from ..simulation import (
    beam_pattern,
    build_scenario,
    coverage_curve,
    diagnose_from_metrics,
    interference_scenario,
    link_budget,
    multi_user_beam_allocation,
    optimize_power,
)


@dataclass
class AgentResult:
    agent: str
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    charts: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    """工具型 Agent 基类：输入意图与实体，输出可解释结果。"""

    name = "base"
    description = ""

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        raise NotImplementedError


class LinkAgent(Agent):
    name = "LinkSimulationAgent"
    description = "链路预算 / 覆盖曲线 / 香农容量仿真"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        dist = entities.get("distance_m", 200.0)
        carrier = entities.get("carrier_ghz", 3.5)
        bw = entities.get("bandwidth_mhz", 100.0)
        ptx = entities.get("power_dbm", 46.0)
        env = entities.get("environment", "urban")

        lb = link_budget(
            distance_m=dist,
            carrier_ghz=carrier,
            bandwidth_mhz=bw,
            tx_power_dbm=ptx,
            environment=env,
        )
        cov = coverage_curve(
            radius_m=max(dist * 1.5, 500.0),
            samples=20,
            carrier_ghz=carrier,
            bandwidth_mhz=bw,
            tx_power_dbm=ptx,
            environment=env,
        )
        chart = {
            "type": "line",
            "title": "覆盖曲线：距离 vs SNR / 吞吐",
            "x_key": "distance_m",
            "series": [
                {"name": "SNR (dB)", "y_key": "snr_db"},
                {"name": "吞吐 (Mbps)", "y_key": "capacity_mbps"},
            ],
            "points": cov["points"],
        }
        msg = (
            f"链路预算完成：d={dist} m, fc={carrier} GHz, B={bw} MHz → "
            f"路损 {lb['path_loss_db']} dB，接收功率 {lb['rx_power_dbm']} dBm，"
            f"SNR {lb['snr_db']} dB，理论容量 {lb['capacity_mbps']} Mbps（{lb['link_quality']}）。"
            f"{cov['summary']}。"
        )
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data={"link_budget": lb, "coverage": cov},
            charts=[chart],
        )


class BeamAgent(Agent):
    name = "BeamformingAgent"
    description = "波束赋形方向图与多用户波束分配"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        n = entities.get("n_elements", 16)
        users = entities.get("ue_count", 4)
        pattern = beam_pattern(n_elements=n, max_gain_dbi=min(10 + 10 * __import__("math").log10(n), 30))
        alloc = multi_user_beam_allocation(n_users=min(users, 16), n_elements=n)
        chart = {
            "type": "line",
            "title": f"水平面方向图（{n} 阵元 ULA）",
            "x_key": "azimuth_deg",
            "series": [{"name": "增益 (dBi)", "y_key": "gain_dbi"}],
            "points": pattern["points"],
        }
        msg = f"{pattern['summary']}。多用户分配：{alloc['summary']}。"
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data={"pattern": pattern, "allocation": alloc},
            charts=[chart],
        )


class InterferenceAgent(Agent):
    name = "InterferenceAgent"
    description = "同频干扰分析与 SINR 评估"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        serving = entities.get("distance_m", 150.0)
        n_i = entities.get("n_interferers", 2)
        result = interference_scenario(
            n_interferers=n_i,
            serving_distance_m=serving,
            carrier_ghz=entities.get("carrier_ghz", 3.5),
            bandwidth_mhz=entities.get("bandwidth_mhz", 100.0),
            tx_power_dbm=entities.get("power_dbm", 46.0),
        )
        msg = (
            f"{result['summary']}，容量约 {result.get('capacity_mbps', 'N/A')} Mbps，"
            f"链路质量：{result.get('link_quality', 'N/A')}。"
        )
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data=result,
            charts=[],
        )


class DiagnoseAgent(Agent):
    name = "DiagnosisAgent"
    description = "KPI 根因诊断与处置建议"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        # 从问题里尽量抠 KPI；缺失则用演示默认
        metrics = {}
        if "sinr_db" in entities:
            metrics["sinr_db"] = entities["sinr_db"]
        elif "db_value" in entities and ("sinr" in query.lower() or "信噪" in query or "干扰" in query):
            metrics["sinr_db"] = entities["db_value"]
        if "rsrp_dbm" in entities:
            metrics["rsrp_dbm"] = entities["rsrp_dbm"]
        elif "power_dbm" in entities and ("rsrp" in query.lower() or "覆盖" in query or "接收" in query):
            metrics["rsrp_dbm"] = entities["power_dbm"]
        if "distance_m" in entities:
            metrics["distance_m"] = entities["distance_m"]
        if "bler" in entities:
            metrics["bler"] = entities["bler"]
        # 默认：典型劣化场景，保证可演示
        metrics.setdefault("sinr_db", -2.0)
        metrics.setdefault("rsrp_dbm", -105.0)
        metrics.setdefault("interference_dbm", -95.0)
        metrics.setdefault("bler", 0.12)
        metrics.setdefault("prb_utilization", 0.92)

        result = diagnose_from_metrics(**metrics)
        top = result["findings"][0]
        msg = f"诊断结论（{result['overall']}）：{top['reason']} 建议：{top['suggestion']}"
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data={"metrics_used": metrics, **result},
            charts=[],
        )


class OptimizeAgent(Agent):
    name = "ResourceOptimizationAgent"
    description = "功率/资源启发式优化"

    def __init__(self) -> None:
        self._scenario: dict[str, Any] | None = None

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        n_bs = entities.get("n_bs", 3)
        n_ue = entities.get("ue_count", 20)
        # 演示默认从 40 dBm 起步，给优化留出提升空间（更易看出前后对比）
        ptx = entities.get("power_dbm", 40.0)
        scenario = self._scenario or build_scenario(
            n_bs=n_bs, n_ue=n_ue, tx_power_dbm=ptx
        )
        self._scenario = scenario
        opt = optimize_power(scenario)
        self._scenario = opt.get("scenario_after", scenario)
        msg = opt["summary"] + " " + "；".join(
            f"{a['bs_id']}:{a['action']} {a['from_dbm']}→{a['to_dbm']}dBm" for a in opt["actions"]
        )
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data=opt,
            charts=[],
        )


class NetworkAgent(Agent):
    name = "NetworkScenarioAgent"
    description = "蜂窝拓扑与 KPI 汇总"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        scenario = build_scenario(
            n_bs=entities.get("n_bs", 3),
            n_ue=entities.get("ue_count", 20),
            carrier_ghz=entities.get("carrier_ghz", 3.5),
            bandwidth_mhz=entities.get("bandwidth_mhz", 100.0),
            tx_power_dbm=entities.get("power_dbm", 46.0),
            environment=entities.get("environment", "urban"),
        )
        stats = scenario["stats"]
        msg = (
            f"场景生成：{scenario['params']['n_bs']} 基站 / {scenario['params']['n_ue']} 用户。"
            f"平均 SINR {stats['avg_sinr_db']} dB，最差 {stats['min_sinr_db']} dB，"
            f"平均容量 {stats['avg_capacity_mbps']} Mbps，弱覆盖 UE {stats['weak_ue_count']} 个。"
        )
        chart = {
            "type": "scatter",
            "title": "用户 SINR 分布",
            "x_key": "distance_m",
            "series": [{"name": "SINR (dB)", "y_key": "sinr_db"}],
            "points": [
                {"distance_m": k["distance_m"], "sinr_db": k["sinr_db"], "ue_id": k["ue_id"]}
                for k in scenario["kpis"]
            ],
        }
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data=scenario,
            charts=[chart],
        )


class CasualAgent(Agent):
    """闲聊 / 寒暄 / 泛问 —— 不进仿真，回得像个人。"""

    name = "CasualAgent"
    description = "日常对话与轻松回应"

    _GREET = [
        "哈喽～我是 CommAgent，通信网络的小工兵。想算指标、查问题，或者随便聊聊都行。",
        "在的！你是想问网络的事，还是就想打个招呼？我都不介意 :)",
        "嗨，来了来了。链路、波束、干扰、诊断，你点哪个我干哪个。",
    ]
    _THANKS = [
        "不客气～还有要跑的指令随时喊我。",
        "小事！下次有 KPI 要看，直接甩过来就行。",
        "应该的。要是还想让我算点啥，说一声就好。",
    ]
    _BYE = [
        "好嘞，先这样。回头有告警或者覆盖问题再来找我。",
        "拜拜～记得右上角还能换模型，答辩前可以切到云端。",
        "撤了撤了，有事随时来运维台敲我。",
    ]
    _WHO = [
        "我是 CommAgent：一套面向 6G 通感算智的运维台。我能算链路预算、画波束、查干扰、做根因诊断、优化功率，还能出报告。你也可以把我当成能聊天的通信实验台。",
        "简单说，我就是你的通信运维搭子——专业活靠确定性仿真，说话我尽量讲人话。",
    ]
    _JOKE = [
        "为什么 SINR 从不去夜店？——因为旁边全是干扰。",
        "香农说：带宽不够就多开点；我说：带宽不够就多开点玩笑。",
        "天线阵列最怕什么？怕大家一齐转向，然后集体丢锁。",
    ]
    _MOOD = [
        "我也就绪得挺稳定的，一路绿灯。你要是累了，咱们先歇口气再算。",
        "服务器精神抖擞。你那边呢？要不先喝口水，再决定要不要跑仿真。",
    ]
    _FALLBACK = [
        "这个我听懂了个大概。你是想跟我聊两句，还是想让我干点网络上的活？比如：",
        "嗯嗯，有收到。不过要不要顺手来点硬活？我这边这几个很好使：",
        "好呀。要是没别的事，你也可以随便点下面这些试试：",
    ]

    _SAMPLES = [
        "帮我做 3.5GHz 200m 的链路预算",
        "SINR -2dB，帮我诊断一下",
        "优化功率提升小区吞吐",
    ]

    def _pick(self, pool: list[str], key: str) -> str:
        # 稳定但可复现的随机：用 key 哈希挑一句
        return pool[abs(hash(key)) % len(pool)]

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        text = (query or "").strip()
        low = text.lower()

        if any(k in text for k in ("再见", "拜拜", "晚安", "走了", "下次")):
            msg = self._pick(self._BYE, text)
        elif any(k in text for k in ("谢谢", "感谢", "多谢", "辛苦")):
            msg = self._pick(self._THANKS, text)
        elif any(k in text for k in ("你是谁", "你叫什么", "介绍下你", "介绍一下你", "你是ai", "你是机器人", "你是谁呀")):
            msg = self._pick(self._WHO, text)
        elif any(k in text for k in ("笑话", "逗我", "唱歌")):
            msg = self._pick(self._JOKE, text)
        elif any(k in text for k in ("累", "心情", "开心", "难过", "无聊", "天气", "吃饭", "睡")):
            msg = self._pick(self._MOOD, text)
        elif any(k in low for k in ("你好", "hi", "hello", "嗨", "在吗", "在么", "早上好", "晚上好", "下午好")) or len(text) <= 4:
            msg = self._pick(self._GREET, text)
        else:
            lead = self._pick(self._FALLBACK, text)
            msg = lead + "\n\n" + "\n".join(f"· {s}" for s in self._SAMPLES)

        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data={"tone": "casual"},
            charts=[],
        )


class HelpAgent(Agent):
    name = "HelpAgent"
    description = "用法引导与示例问题"

    SAMPLES = [
        "帮我做 3.5GHz 100MHz 带宽、距离 200m 的链路预算和覆盖曲线",
        "分析 16 阵元波束赋形方向图和多用户波束分配",
        "服务距离 150m，2 个同频干扰源，分析 SINR",
        "SINR 是 -2dB，BLER 0.12，帮我做根因诊断",
        "3 个基站 20 个用户组网，优化功率提升吞吐",
        "生成一份网络仿真与诊断报告",
        "什么是香农公式和它的工程意义？",
    ]

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        text = query or ""
        wants = []
        if any(k in text for k in ["问", "示例", "举例", "问题"]):
            wants.append("questions")
        if any(k in text for k in ["用", "功能", "能做", "怎么"]):
            wants.append("usage")
        if not wants:
            wants = ["questions", "usage"]

        lines = ["下面是几条你可以直接输入的运维指令：", ""]
        for i, s in enumerate(self.SAMPLES, 1):
            lines.append(f"{i}. {s}")

        if "usage" in wants:
            lines += [
                "",
                "怎么用：",
                "· 直接说人话下指令，我会自动拆给链路 / 波束 / 干扰 / 诊断 / 优化引擎",
                "· 也可以点对话框下方的快捷标签",
                "· 右上角「模型设置」可切换离线演示或云端大模型",
                "· 侧栏还有表单式仿真页，适合精确调参",
            ]
        msg = "\n".join(lines)
        return AgentResult(
            agent=self.name,
            success=True,
            message=msg,
            data={"samples": self.SAMPLES},
            charts=[],
        )


class KnowledgeAgent(Agent):
    name = "KnowledgeAgent"
    description = "通信知识 RAG 问答"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        hits = search_knowledge(query, top_k=3)
        if not hits:
            hits = search_knowledge("通信 智能体 6G", top_k=2)
        if not hits:
            return AgentResult(
                agent=self.name,
                success=True,
                message="知识库里暂时没有直接匹配。你可以换个关键词（香农 / 波束 / 干扰 / 6G），或输入「给我几个可以问的问题」看示例。",
                data={"hits": []},
            )
        # 更自然的答复，而不是机械堆砌
        head = f"关于「{query.strip()}」，我查到这些通信知识："
        parts = [head, ""]
        for i, h in enumerate(hits, 1):
            body = h["content"]
            # 稍微截断，避免一屏全是字
            if len(body) > 160:
                body = body[:160].rstrip() + "…"
            parts.append(f"{i}. **{h['title']}**（{h['category']}）")
            parts.append(f"   {body}")
            parts.append("")
        parts.append("想动手验证的话，可以直接说：「帮我算 3.5GHz 200m 的链路预算」。")
        return AgentResult(
            agent=self.name,
            success=True,
            message="\n".join(parts),
            data={"hits": hits},
        )


class ReportAgent(Agent):
    name = "ReportAgent"
    description = "运维/仿真报告生成"

    def run(self, intent: str, entities: dict[str, Any], query: str) -> AgentResult:
        # 汇总一次典型仿真作为报告主体
        lb = link_budget(distance_m=entities.get("distance_m", 200.0))
        diag = diagnose_from_metrics(sinr_db=lb["snr_db"], distance_m=entities.get("distance_m", 200.0))
        report = {
            "title": "CommAgent 网络仿真与诊断报告",
            "sections": [
                {
                    "heading": "1. 仿真配置",
                    "body": f"距离 {lb['inputs']['distance_m']} m，载波 {lb['inputs']['carrier_ghz']} GHz，"
                    f"带宽 {lb['inputs']['bandwidth_mhz']} MHz，发射功率 {lb['inputs']['tx_power_dbm']} dBm。",
                },
                {
                    "heading": "2. 链路结果",
                    "body": f"路损 {lb['path_loss_db']} dB，接收功率 {lb['rx_power_dbm']} dBm，"
                    f"SNR {lb['snr_db']} dB，容量 {lb['capacity_mbps']} Mbps，评价：{lb['link_quality']}。",
                },
                {
                    "heading": "3. 诊断与建议",
                    "body": "；".join(f"[{f['level']}] {f['reason']} → {f['suggestion']}" for f in diag["findings"]),
                },
                {
                    "heading": "4. 结论",
                    "body": "链路预算与诊断均由 CommAgent 确定性仿真引擎生成，可复现、可审计。"
                    "建议按诊断建议优先级实施功率/波束/干扰协调优化。",
                },
            ],
            "meta": {"generator": "CommAgent ReportAgent", "mode": "offline-deterministic"},
        }
        return AgentResult(
            agent=self.name,
            success=True,
            message=f"报告已生成：《{report['title']}》，共 {len(report['sections'])} 节，可在「报告」页查看。",
            data={"report": report},
        )


class Orchestrator:
    """意图 → Agent 路由 + 可选 LLM 说明 + 结果聚合。"""

    def __init__(self) -> None:
        self.link = LinkAgent()
        self.beam = BeamAgent()
        self.interf = InterferenceAgent()
        self.diagnose = DiagnoseAgent()
        self.optimize = OptimizeAgent()
        self.network = NetworkAgent()
        self.knowledge = KnowledgeAgent()
        self.report = ReportAgent()
        self.help = HelpAgent()
        self.casual = CasualAgent()
        self.llm = get_llm()
        self._routes: dict[str, Callable[[str, dict, str], AgentResult]] = {
            "casual": self.casual.run,
            "simulate_link": self.link.run,
            "simulate_beam": self.beam.run,
            "simulate_interference": self.interf.run,
            "diagnose": self.diagnose.run,
            "optimize": self.optimize.run,
            "network": self.network.run,
            "knowledge": self.knowledge.run,
            "report": self.report.run,
            "help": self.help.run,
            "general": self.casual.run,
        }

    def handle(self, query: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        classification = classify_intent(query)
        intent = classification["intent"]
        entities = classification["entities"]
        history = history or []

        # 概念/原理类问题（没有具体数值要仿真）→ 知识融进对话，别硬派仿真
        conceptual = bool(re.search(r"为什么|什么原因|怎么回事|如何理解|啥原理|有什么区别|哪个好|优缺点", query or ""))
        has_num = bool(entities)
        soft_intents = {"casual", "general", "help", "knowledge"}
        if conceptual and not has_num and intent not in ("casual", "help"):
            intent = "knowledge"
        if intent in soft_intents:
            # 检索领域知识，交给模型「揉」进回答（闲聊少给或不给）
            context_hits = []
            if intent in ("knowledge", "general") or any(
                k in (query or "") for k in (
                    "信道", "路损", "覆盖", "干扰", "波束", "mimo", "香农", "容量", "sinr",
                    "6g", "调制", "天线", "组网", "基站", "吞吐", "时延",
                )
            ):
                context_hits = search_knowledge(query, top_k=3)

            reply, source = conversation_reply(
                query, history, prefer_api=True, knowledge=context_hits
            )

            # 离线且有知识：补一点干货，但口吻克制
            if context_hits and source == "mock":
                bullets = "\n".join(
                    f"· {h['title']}：{h['content'][:90]}" for h in context_hits[:2]
                )
                reply = f"{reply}\n\n顺带一提：\n{bullets}"

            return {
                "query": query,
                "intent": intent,
                "confidence": classification["confidence"],
                "entities": entities,
                "agent": "ConversationAgent" if source == "api" else (
                    "CasualAgent" if intent in ("casual", "general") else "HelpAgent"
                ),
                "success": True,
                "message": reply,
                "llm_note": "",
                "data": {"tone": "chat", "source": source, "knowledge": [
                    {"title": h.get("title"), "category": h.get("category")} for h in context_hits
                ]},
                "charts": [],
                "light": True,
            }

        # —— 专业工具任务：确定性仿真 + 模型解释 ——
        runner = self._routes.get(intent, self.casual.run)
        try:
            result = runner(intent, entities, query)
        except Exception as exc:
            result = AgentResult(
                agent="Orchestrator",
                success=False,
                message=f"哎呀，这步没跑利索：{exc}。要不换个说法再试一次？",
                data={},
            )

        # 专业知识：检索 + 让模型用工程口吻解释结果（不是贴公式清单）
        tool_hits = search_knowledge(query or intent, top_k=2)
        llm_note = ""
        try:
            kn = "\n".join(f"- {h.get('title')}：{(h.get('content') or '')[:180]}" for h in tool_hits)
            sys = (
                "你是通信工程专家。用 2～4 句自然的话解释下面的仿真结果，"
                "把相关原理顺带说清楚（别用「根据以下结果」这种套话，也别列一堆条目）。"
            )
            if kn:
                sys += "\n参考知识（揉进话里）：\n" + kn
            llm_note = self.llm.chat(
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"用户问题：{query}\n工具结果：{result.message}"},
                ]
            )
        except Exception:
            llm_note = ""

        return {
            "query": query,
            "intent": intent,
            "confidence": classification["confidence"],
            "entities": entities,
            "agent": result.agent,
            "success": result.success,
            "message": result.message,
            "llm_note": llm_note,
            "data": result.data,
            "charts": result.charts,
            "light": False,
        }
