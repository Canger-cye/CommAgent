"""LLM 抽象层：可插拔 Mock / 云端 OpenAI 兼容 API。"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..config import settings


class BaseLLM(ABC):
    """统一聊天接口。"""

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> str:
        """messages: [{"role": "user"|"system"|"assistant", "content": "..."}]"""

    def chat_text(self, user: str, system: str | None = None, history: list[dict[str, str]] | None = None,
                  *, temperature: float = 0.3) -> str:
        """便捷方法：system + 历史 + 最新用户消息。"""
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        for h in history or []:
            role = h.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"
            content = (h.get("content") or "").strip()
            if content:
                msgs.append({"role": role, "content": content})
        msgs.append({"role": "user", "content": user})
        return self.chat(msgs, temperature=temperature)


class MockLLM(BaseLLM):
    """离线可运行的确定性推理层。

    用规则解析意图并调用仿真/诊断工具，保证答辩现场无网也能完整演示。
    真正的大模型接入见 OpenAILLM。
    """

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> str:
        user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user = m.get("content", "")
                break

        # 工具结果润色：短、口语一点
        if "工具结果" in user or "已完成" in user or "链路预算完成" in user:
            return "数值都算好了，就摆在下面。有想改的参数直接说～"

        intent = classify_intent(user)
        name = intent["intent"]
        if name == "casual":
            return "在的在的～想聊两句也行，想算网络指标也行。"
        if name == "help":
            return "行，我给你列几个现成的指令，直接点或复制都好使。"
        if name in ("simulate_link", "simulate_beam", "simulate_interference"):
            return "收到，这就去跑仿真。"
        if name == "diagnose":
            return "好，我按「覆盖 → 干扰 → 负载」的顺序帮你排一遍。"
        if name == "optimize":
            return "行，我先看现网功率，再搜一版更好吃的结果。"
        if name == "report":
            return "没问题，我把刚才的结论整理成一页报告。"
        return "嗯，我先看看你想问啥，再决定叫哪个引擎出手。"


class OpenAILLM(BaseLLM):
    """OpenAI 兼容 Chat Completions API。"""

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_base = (api_base or settings.llm_api_base).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.3) -> str:
        if not self.api_key:
            raise RuntimeError("未配置 COMMAGENT_LLM_API_KEY，无法调用云端 LLM")
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        if isinstance(content, list):
            # 兼容部分端点的 content 分块格式
            content = "".join(
                (c.get("text") or "") if isinstance(c, dict) else str(c) for c in content
            )
        return content.strip() or "（模型没有返回文本）"


# 通信运维助手人设：自由对话时用
COMMAgent_SYSTEM = (
    "你是 CommAgent，全球校园人工智能算法精英大赛参赛作品「6G 通感算智网络智能运维体」的对话助手。"
    "性格：自然、简短、有人味，像通信工程的学长/同事，不要客服腔，不要干巴巴的条目堆砌。\n"
    "专业素养：回答通信/网络问题时，把原理「揉」进句子里顺带讲清楚"
    "（比如路损随距离对数增长、干扰受限时抬功率往往没用、香农容量对 SNR 是对数关系），"
    "而不是先贴一段公式再列几点。\n"
    "能力：链路预算、波束赋形、干扰分析、KPI 根因诊断、功率优化、运维报告。"
    "闲聊要接住；专业问题给可信结论和可操作建议。\n"
    "回答尽量 2～6 句，中文，像在工位旁边聊天。"
)


def conversation_reply(
    user: str,
    history: list[dict[str, str]] | None = None,
    *,
    prefer_api: bool = True,
    knowledge: list[dict] | None = None,
) -> tuple[str, str]:
    """自由对话：优先真模型，失败则回退离线话术。

    knowledge: 检索到的领域知识，会融进模型提示，避免空泛回答。
    返回 (reply, source)  source: api | mock
    """
    history = history or []
    if prefer_api:
        try:
            llm = get_llm()
            if isinstance(llm, OpenAILLM):
                sys_prompt = COMMAgent_SYSTEM
                if knowledge:
                    kn = "\n".join(
                        f"- {h.get('title', '')}：{(h.get('content') or '')[:220]}" for h in knowledge
                    )
                    sys_prompt += (
                        "\n\n下面是从通信知识库检索到的背景，请自然地融进回答"
                        "（不要说「根据知识库」，也不要原样大段抄）：\n" + kn
                    )
                text = llm.chat_text(
                    user,
                    system=sys_prompt,
                    history=history[-10:],
                    temperature=settings.llm_temperature,
                )
                if text and text != "（模型没有返回文本）":
                    return text, "api"
        except Exception:
            pass

    # 离线回退：规则话术
    from .fallback_chat import offline_reply

    return offline_reply(user), "mock"


def get_llm() -> BaseLLM:
    """按配置返回 LLM 实例。"""
    mode = (settings.llm_mode or "mock").lower()
    if mode == "api":
        return OpenAILLM()
    return MockLLM()


# ---------- 意图识别（Mock 路径与工具路由共用） ----------

INTENT_PATTERNS: list[tuple[str, list[str], float]] = [
    # 闲聊 / 社交 —— 不要进仿真调度
    ("casual", [
        "你好", "您好", "hi", "hello", "嗨", "哈喽", "在吗", "在么",
        "谢谢", "感谢", "多谢", "辛苦", "厉害", "牛", "棒", "不错",
        "再见", "拜拜", "晚安", "早上好", "下午好", "晚上好",
        "你是谁", "介绍下你", "介绍一下你", "你叫什么", "你是ai", "你是机器人",
        "怎么样", "还好吗", "最近", "无聊", "哈哈", "嘻嘻", "呜呜", "呜呜呜",
        "天气", "吃饭", "睡觉", "累", "加油", "开心", "难过", "心情",
        "讲个笑话", "说个笑话", "来个笑话", "逗我", "唱首歌",
        "爱你", "么么", "嘿嘿", "牛逼", "nb", "yyds", "绝了",
        "随便", "无所谓", "不知道", "随便问问", "没事", "好的", "ok", "okay", "嗯", "哦",
        "可以吗", "行不行", "是不是", "对不对", "真的吗", "为什么呀",
    ], 1.2),
    ("help", ["可以问", "能问", "问什么", "示例问题", "举例", "怎么用", "怎么使用", "如何使用", "如何用",
              "用法", "使用方法", "能做什么", "有哪些功能", "功能有哪些", "帮助", "使用说明",
              "指令", "guide", "help", "example", "提问", "介绍下", "介绍一下"], 1.5),
    ("report", ["报告", "周报", "生成报告", "运维报告", "仿真报告"], 1.2),
    ("diagnose", ["诊断", "告警", "根因", "故障", "为什么", "异常", "kpi", "rsrp", "bler", "排查"], 0.85),
    ("optimize", ["优化", "调度", "功率", "资源", "负载", "提升速率", "改善"], 0.85),
    ("simulate_link", ["链路预算", "链路", "覆盖曲线", "覆盖", "snr", "吞吐", "容量", "路损", "仿真", "距离"], 0.8),
    ("simulate_beam", ["波束赋形", "波束", "beam", "阵列", "天线", "波束宽度", "mimo", "赋形"], 0.85),
    ("simulate_interference", ["干扰", "同频", "邻区", "sinr", "icic"], 0.8),
    ("network", ["基站", "小区", "拓扑", "场景", "ue", "用户数", "组网"], 0.75),
    ("knowledge", ["什么是", "解释", "原理", "公式", "概念", "区别", "香农", "mimo", "6g"], 0.7),
]


def classify_intent(text: str) -> dict[str, Any]:
    """关键词 + 实体抽取，供编排器路由。"""
    raw = text or ""
    q = raw.lower().strip()
    scores: dict[str, float] = {}
    for intent, kws, weight in INTENT_PATTERNS:
        for kw in kws:
            if kw in q:
                scores[intent] = scores.get(intent, 0.0) + weight

    entities = extract_entities(raw)

    # 短寒暄强判定：一两个词的招呼/感谢/语气词，直接走闲聊
    stripped = re.sub(r"[，。！？~、\s!?.…]+", "", q)
    casual_short = any(stripped in (kw, kw + "呀", kw + "啊", kw + "哦") for kw in (
        "你好", "您好", "hi", "hello", "嗨", "在吗", "谢谢", "感谢", "好的", "ok",
        "嗯", "哦", "哈哈", "再见", "拜拜", "晚安", "加油", "好", "行", "行吧", "可以",
    ))
    if casual_short or (len(stripped) <= 4 and scores.get("casual", 0) > 0):
        return {"intent": "casual", "confidence": 0.92, "entities": entities}

    if not scores:
        # 疑问句且没有专业词 → 当成泛聊/介绍，别硬塞知识库
        if re.search(r"[？?]|吗|呢|呀|什么|怎么|谁|哪", raw) and not entities:
            return {"intent": "casual", "confidence": 0.55, "entities": entities}
        if len(stripped) <= 12 and not entities:
            return {"intent": "casual", "confidence": 0.5, "entities": entities}
        intent = "general"
        confidence = 0.4
    else:
        intent = max(scores, key=lambda k: scores[k])
        confidence = min(0.95, 0.5 + scores[intent] * 0.15)

    return {"intent": intent, "confidence": round(confidence, 2), "entities": entities}


def extract_entities(text: str) -> dict[str, Any]:
    """从自然语言抽取数值实体。"""
    ent: dict[str, Any] = {}
    t = text or ""

    def _num(pattern: str, key: str, cast=float):
        m = re.search(pattern, t, re.I)
        if m:
            try:
                ent[key] = cast(m.group(1))
            except ValueError:
                pass

    _num(r"(-?\d+(?:\.\d+)?)\s*(?:ghz|GHz|吉赫)", "carrier_ghz")
    _num(r"(-?\d+(?:\.\d+)?)\s*(?:mhz|MHz|兆赫)", "bandwidth_mhz")
    _num(r"(?:RSRP|rsrp|接收功率|参考信号)[^-\d]{0,8}(-?\d+(?:\.\d+)?)\s*(?:dbm|dBm)", "rsrp_dbm")
    _num(r"(?:SINR|sinr|信噪|信干噪|SIR)[^-\d]{0,8}(-?\d+(?:\.\d+)?)\s*(?:db|dB)", "sinr_db")
    _num(r"(-?\d+(?:\.\d+)?)\s*(?:dbm|dBm)", "power_dbm")
    _num(r"(-?\d+(?:\.\d+)?)\s*(?:db|dB)(?![a-zA-Z])", "db_value")
    _num(r"(-?\d+(?:\.\d+)?)\s*(?:m|米)(?![a-zA-Z])", "distance_m")
    _num(r"(\d+)\s*(?:个)?(?:用户|ue|UE)", "ue_count", int)
    _num(r"(\d+)\s*(?:个)?(?:基站|小区|bs)", "n_bs", int)
    _num(r"(\d+)\s*(?:个)?(?:同频)?(?:干扰源|干扰|邻区)", "n_interferers", int)
    _num(r"(\d+)\s*阵元", "n_elements", int)
    _num(r"(?:BLER|bler|误块率)\s*(?:是|为|:|：)?\s*(0?\.\d+|\d+)", "bler")

    # 负 dB 单独兜底，例如 "SINR 是 -2dB"
    m = re.search(r"(-\d+(?:\.\d+)?)\s*dB", t)
    if m and "db_value" not in ent and "sinr_db" not in ent:
        ent["db_value"] = float(m.group(1))

    if re.search(r"农村|rural", t, re.I):
        ent["environment"] = "rural"
    elif re.search(r"室内|indoor", t, re.I):
        ent["environment"] = "indoor"
    elif re.search(r"城区|城市|urban|市区", t, re.I):
        ent["environment"] = "urban"

    return ent
