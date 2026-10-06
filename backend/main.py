"""CommAgent FastAPI 入口：API + 静态前端。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agents import Orchestrator
from .config import FRONTEND_DIR, save_persisted_llm, settings
from .knowledge import KNOWLEDGE_BASE
from .llm import classify_intent, get_llm
from .simulation import (
    beam_pattern,
    build_scenario,
    coverage_curve,
    diagnose_from_metrics,
    interference_scenario,
    link_budget,
    multi_user_beam_allocation,
    optimize_power,
)

FRONTEND_DIR = FRONTEND_DIR  # 来自 config，兼容打包后路径

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户自然语言指令")
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description="多轮对话历史，元素形如 {role: user|assistant, content: ...}",
    )


class LinkRequest(BaseModel):
    distance_m: float = 200.0
    carrier_ghz: float = 3.5
    bandwidth_mhz: float = 100.0
    tx_power_dbm: float = 46.0
    tx_gain_dbi: float = 18.0
    rx_gain_dbi: float = 0.0
    noise_figure_db: float = 7.0
    environment: str = "urban"
    interference_dbm: float | None = None


class BeamRequest(BaseModel):
    n_elements: int = 16
    max_gain_dbi: float = 18.0
    beamwidth_3db_deg: float = 65.0
    tilt_deg: float = 0.0
    n_users: int = 4


class DiagnoseRequest(BaseModel):
    sinr_db: float | None = None
    throughput_mbps: float | None = None
    bler: float | None = None
    rsrp_dbm: float | None = None
    interference_dbm: float | None = None
    prb_utilization: float | None = None
    distance_m: float | None = None


class ScenarioRequest(BaseModel):
    n_bs: int = 3
    n_ue: int = 20
    area_m: float = 1200.0
    seed: int = 42
    carrier_ghz: float = 3.5
    bandwidth_mhz: float = 100.0
    tx_power_dbm: float = 46.0
    environment: str = "urban"


class LLMConfigRequest(BaseModel):
    llm_mode: str = Field(..., pattern="^(mock|api)$")
    llm_model: str = ""
    llm_api_base: str = ""
    llm_api_key: str | None = None
    llm_timeout: float = 30.0
    llm_temperature: float = 0.3


class LLMTestRequest(BaseModel):
    llm_mode: str = Field(..., pattern="^(mock|api)$")
    llm_model: str = ""
    llm_api_base: str = ""
    llm_api_key: str | None = None
    llm_timeout: float = 15.0


# 模型预设（页面一键选择）
LLM_PRESETS = [
    {"id": "mock", "name": "本地演示引擎", "mode": "mock", "model": "builtin-rules", "api_base": "", "note": "离线确定性推理，答辩无网可用"},
    {"id": "openai", "name": "OpenAI", "mode": "api", "model": "gpt-4o-mini", "api_base": "https://api.openai.com/v1", "note": "GPT 系列"},
    {"id": "deepseek", "name": "DeepSeek", "mode": "api", "model": "deepseek-chat", "api_base": "https://api.deepseek.com/v1", "note": "性价比高，中文好"},
    {"id": "moonshot", "name": "Moonshot Kimi", "mode": "api", "model": "moonshot-v1-8k", "api_base": "https://api.moonshot.cn/v1", "note": "长上下文"},
    {"id": "qwen", "name": "通义千问 DashScope", "mode": "api", "model": "qwen-plus", "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "note": "阿里云兼容模式"},
    {"id": "zhipu", "name": "智谱 GLM", "mode": "api", "model": "glm-4-flash", "api_base": "https://open.bigmodel.cn/api/paas/v4", "note": "国产大模型"},
    {"id": "custom", "name": "自定义端点", "mode": "api", "model": "", "api_base": "", "note": "任意 OpenAI 兼容接口"},
]


@app.get("/api/health")
def health() -> dict[str, Any]:
    llm = get_llm()
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_mode": settings.llm_mode,
        "llm_class": llm.__class__.__name__,
        "llm_model": settings.llm_model,
        "knowledge_items": len(KNOWLEDGE_BASE),
    }


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return {
        "llm_mode": settings.llm_mode,
        "llm_model": settings.llm_model,
        "default_scenario": settings.default_scenario,
    }


@app.get("/api/llm/config")
def get_llm_config() -> dict[str, Any]:
    return settings.public_dict()


@app.get("/api/llm/presets")
def get_llm_presets() -> dict[str, Any]:
    return {"presets": LLM_PRESETS}


@app.post("/api/llm/config")
def set_llm_config(req: LLMConfigRequest) -> dict[str, Any]:
    payload = {
        "llm_mode": req.llm_mode,
        "llm_model": req.llm_model,
        "llm_api_base": req.llm_api_base,
        "llm_timeout": req.llm_timeout,
        "llm_temperature": req.llm_temperature,
    }
    # key 为空或脱敏占位时不覆盖已有 key
    if req.llm_api_key and req.llm_api_key not in ("", "已设置") and "…" not in req.llm_api_key:
        payload["llm_api_key"] = req.llm_api_key
    save_persisted_llm(payload)
    # 刷新编排器 LLM
    orchestrator.llm = get_llm()
    return {"ok": True, "config": settings.public_dict()}


@app.post("/api/llm/test")
def test_llm(req: LLMTestRequest) -> dict[str, Any]:
    from .llm.base import MockLLM, OpenAILLM

    try:
        if req.llm_mode == "mock":
            note = MockLLM().chat([{"role": "user", "content": "连接测试"}])
            return {"ok": True, "detail": note[:200], "latency_ms": 1}
        api_key = req.llm_api_key or settings.llm_api_key
        if not api_key:
            return {"ok": False, "detail": "请先填写 API Key"}
        import time

        t0 = time.time()
        llm = OpenAILLM(
            api_base=req.llm_api_base or settings.llm_api_base,
            api_key=api_key,
            model=req.llm_model or settings.llm_model,
            timeout=req.llm_timeout,
        )
        note = llm.chat([{"role": "user", "content": "请只回复：连接成功"}])
        return {"ok": True, "detail": note[:200], "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:300]}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    history = []
    for item in req.history[-12:]:
        role = item.get("role", "user")
        content = (item.get("content") or "").strip()
        if content:
            history.append({"role": role, "content": content})
    return orchestrator.handle(req.message, history=history)


@app.post("/api/intent")
def intent_only(req: ChatRequest) -> dict[str, Any]:
    return classify_intent(req.message)


@app.get("/api/link")
def api_link(
    distance_m: float = 200.0,
    carrier_ghz: float = 3.5,
    bandwidth_mhz: float = 100.0,
    tx_power_dbm: float = 46.0,
    environment: str = "urban",
    interference_dbm: float | None = None,
) -> dict[str, Any]:
    lb = link_budget(
        distance_m=distance_m,
        carrier_ghz=carrier_ghz,
        bandwidth_mhz=bandwidth_mhz,
        tx_power_dbm=tx_power_dbm,
        environment=environment,
        interference_dbm=interference_dbm,
    )
    cov = coverage_curve(
        radius_m=max(distance_m * 1.5, 500),
        carrier_ghz=carrier_ghz,
        bandwidth_mhz=bandwidth_mhz,
        tx_power_dbm=tx_power_dbm,
        environment=environment,
    )
    return {"link_budget": lb, "coverage": cov}


@app.post("/api/link")
def api_link_post(req: LinkRequest) -> dict[str, Any]:
    lb = link_budget(**req.model_dump())
    cov = coverage_curve(
        radius_m=max(req.distance_m * 1.5, 500),
        carrier_ghz=req.carrier_ghz,
        bandwidth_mhz=req.bandwidth_mhz,
        tx_power_dbm=req.tx_power_dbm,
        environment=req.environment,
    )
    return {"link_budget": lb, "coverage": cov}


@app.get("/api/beam")
def api_beam(n_elements: int = 16, n_users: int = 4) -> dict[str, Any]:
    import math

    gain = min(10 + 10 * math.log10(max(n_elements, 1)), 30)
    return {
        "pattern": beam_pattern(n_elements=n_elements, max_gain_dbi=gain),
        "allocation": multi_user_beam_allocation(n_users=n_users, n_elements=n_elements),
    }


@app.post("/api/beam")
def api_beam_post(req: BeamRequest) -> dict[str, Any]:
    return {
        "pattern": beam_pattern(
            n_elements=req.n_elements,
            max_gain_dbi=req.max_gain_dbi,
            beamwidth_3db_deg=req.beamwidth_3db_deg,
            tilt_deg=req.tilt_deg,
        ),
        "allocation": multi_user_beam_allocation(n_users=req.n_users, n_elements=req.n_elements),
    }


@app.get("/api/interference")
def api_interference(n_interferers: int = 2, serving_distance_m: float = 150.0) -> dict[str, Any]:
    return interference_scenario(n_interferers=n_interferers, serving_distance_m=serving_distance_m)


@app.post("/api/diagnose")
def api_diagnose(req: DiagnoseRequest) -> dict[str, Any]:
    metrics = {k: v for k, v in req.model_dump().items() if v is not None}
    return diagnose_from_metrics(**metrics)


@app.get("/api/scenario")
def api_scenario(
    n_bs: int = 3,
    n_ue: int = 20,
    seed: int = 42,
    environment: str = "urban",
) -> dict[str, Any]:
    return build_scenario(n_bs=n_bs, n_ue=n_ue, seed=seed, environment=environment)


@app.post("/api/scenario")
def api_scenario_post(req: ScenarioRequest) -> dict[str, Any]:
    return build_scenario(**req.model_dump())


@app.post("/api/optimize")
def api_optimize(req: ScenarioRequest) -> dict[str, Any]:
    scenario = build_scenario(**req.model_dump())
    return optimize_power(scenario)


@app.get("/api/knowledge")
def api_knowledge(q: str = "") -> dict[str, Any]:
    from .knowledge import search_knowledge

    if not q:
        return {"items": KNOWLEDGE_BASE}
    return {"items": search_knowledge(q, top_k=5)}


# ---- 静态前端 ----
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/index.html")
    def index_html() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
