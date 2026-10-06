"""通信领域知识库（轻量关键词检索，离线可用）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KnowledgeItem:
    id: str
    title: str
    category: str
    keywords: list[str]
    content: str


KNOWLEDGE_BASE: list[KnowledgeItem] = [
    KnowledgeItem(
        id="k-shannon",
        title="香农信道容量",
        category="信息论",
        keywords=["香农", "容量", "吞吐", "shannon", "capacity", "C", "带宽", "频谱效率"],
        content=(
            "香农公式：C = B * log2(1 + SNR)，其中 B 为带宽(Hz)，SNR 为线性信噪比。"
            "它给出加性高斯白噪声信道的可靠传输速率上界。工程中常用来估算小区峰值吞吐，"
            "并解释「带宽翻倍」与「功率抬升」对速率的不同贡献：带宽线性提升容量，"
            "SNR 的贡献呈对数增长。"
        ),
    ),
    KnowledgeItem(
        id="k-pathloss",
        title="传播与路损模型",
        category="信道",
        keywords=["路损", "path loss", "传播", "UMa", "38.901", "覆盖", "距离", "自由空间", "FSPL"],
        content=(
            "3GPP TR 38.901 给出 UMa/UMi/RMa/InH 等场景路损模型。"
            "UMa NLOS 简化式：PL = 13.54 + 39.08*log10(d[m]) + 20*log10(fc[GHz])。"
            "自由空间 Friis：FSPL = 32.45 + 20*log10(d) + 20*log10(fc)。"
            "覆盖规划中通常以 RSRP ≥ -110 dBm、SINR ≥ 0 dB 作为边缘可用门限。"
        ),
    ),
    KnowledgeItem(
        id="k-beam",
        title="Massive MIMO 与波束赋形",
        category="天线",
        keywords=["波束", "beamforming", "Massive MIMO", "MIMO", "阵列", "ULA", "增益", "波束宽度"],
        content=(
            "大规模 MIMO 通过大规模天线阵列形成窄波束，将能量集中到目标用户方向。"
            "N 元均匀线阵理想阵列因子峰值增益约 10*log10(N) dB。"
            "波束越窄、增益越高，但对波束对准与用户跟踪要求也越高。"
            "多用户场景可用 ZF/MMSE 预编码在空间上分离用户流。"
        ),
    ),
    KnowledgeItem(
        id="k-interference",
        title="干扰受限与干扰协调",
        category="无线资源",
        keywords=["干扰", "interference", "SINR", "ICIC", "eICIC", "同频", "邻区", "频率复用"],
        content=(
            "现代蜂窝网多为干扰受限而非噪声受限：邻区同频信号抬升干扰底，"
            "使 SINR 恶化。应对手段包括：频率复用加严、波束空间隔离、功率回退、"
            "ICIC/eICIC 干扰协调、CoMP 联合传输。诊断时先比较 I 与 N，"
            "若 I >> N 则应优先做干扰管理而非加大功率。"
        ),
    ),
    KnowledgeItem(
        id="k-kpi",
        title="网络 KPI 与根因分析",
        category="运维",
        keywords=["KPI", "RSRP", "SINR", "BLER", "误块率", "PRB", "负载", "根因", "告警", "诊断"],
        content=(
            "常见 KPI：RSRP（覆盖）、SINR（质量）、BLER（可靠性）、PRB 利用率（负载）、"
            "吞吐/时延（体验）。根因分析遵循「覆盖→干扰→负载→终端/参数」排查顺序："
            "RSRP 差看覆盖，RSRP 好 SINR 差看干扰，SINR 好吞吐低看负载与 MCS，"
            "BLER 高看上行干扰或功控。"
        ),
    ),
    KnowledgeItem(
        id="k-6g",
        title="6G 通感算智一体化",
        category="6G",
        keywords=["6G", "通感", "算力", "智算", "ISAC", "空天地", "低空", "内生智能", "数字孪生"],
        content=(
            "6G 愿景强调通感算智一体化（ISAC + AI + 算力网络）：通信与雷达感知共享波形，"
            "网络内生智能完成意图驱动运维，算力网络调度训练/推理任务。"
            "典型场景包括低空经济、空天地一体化、全息通信、沉浸式交互。"
            "数字孪生作为网络的影子系统，可支撑 what-if 仿真与智能体闭环决策。"
        ),
    ),
    KnowledgeItem(
        id="k-agent",
        title="通信网络智能体架构",
        category="AI智能体",
        keywords=["智能体", "Agent", "意图", "编排", "多智能体", "LLM", "RAG", "数字孪生"],
        content=(
            "通信运维智能体通常分层：意图理解层（NLU→运维意图）、"
            "规划编排层（拆解子任务）、工具/仿真层（链路预算、干扰分析、功率优化）、"
            "知识层（RAG 检索通信规范/案例）、执行与报告层。"
            "关键工程原则：LLM 负责推理与自然语言交互，数值仿真与优化求解由确定性算法完成，"
            "保证结果可复现、可审计。"
        ),
    ),
]


def search_knowledge(query: str, top_k: int = 3) -> list[dict]:
    """基于关键词重叠的轻量检索。"""
    q = (query or "").lower()
    if not q:
        return []
    scored = []
    for item in KNOWLEDGE_BASE:
        score = 0
        blob = (item.title + item.category + item.content).lower()
        for kw in item.keywords:
            if kw.lower() in q:
                score += 3
            if kw.lower() in blob:
                score += 1
        # 标题包含
        for token in q.replace("？", " ").replace("?", " ").split():
            if token and token in item.title.lower():
                score += 2
            if token and token in item.content.lower():
                score += 1
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    results = []
    for score, item in scored[:top_k]:
        results.append(
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "content": item.content,
                "score": score,
            }
        )
    return results
