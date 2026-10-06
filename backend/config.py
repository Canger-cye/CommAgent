"""CommAgent 全局配置（支持运行时覆盖）。"""
from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _resolve_base() -> Path:
    """开发：commagent/；打包后：exe 所在目录（便于便携保存配置）。"""
    if getattr(sys, "frozen", False):
        env = os.getenv("COMMAGENT_DATA_DIR")
        return Path(env) if env else Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _resolve_resource() -> Path:
    """静态资源/代码：打包后在 _MEIPASS。"""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parent.parent


BASE_DIR = _resolve_base()
RESOURCE_DIR = _resolve_resource()
DEMO_DATA_DIR = RESOURCE_DIR / "demo_data"
FRONTEND_DIR = RESOURCE_DIR / "frontend"
OUTPUT_DIR = BASE_DIR / "outputs"
CONFIG_FILE = OUTPUT_DIR / "llm_config.json"


@dataclass
class Settings:
    """运行时配置，优先读环境变量，便于答辩现场切换。"""

    app_name: str = "CommAgent · 6G通感算智网络智能运维体"
    host: str = os.getenv("COMMAGENT_HOST", "127.0.0.1")
    port: int = int(os.getenv("COMMAGENT_PORT", "8787"))

    # llm_mode: mock | api
    llm_mode: str = os.getenv("COMMAGENT_LLM_MODE", "mock")
    llm_api_base: str = os.getenv("COMMAGENT_LLM_API_BASE", "https://api.openai.com/v1")
    llm_api_key: str = os.getenv("COMMAGENT_LLM_API_KEY", "")
    llm_model: str = os.getenv("COMMAGENT_LLM_MODEL", "gpt-4o-mini")
    llm_timeout: float = float(os.getenv("COMMAGENT_LLM_TIMEOUT", "30"))
    llm_temperature: float = float(os.getenv("COMMAGENT_LLM_TEMPERATURE", "0.3"))

    # 默认仿真场景参数
    default_scenario: dict = field(
        default_factory=lambda: {
            "carrier_ghz": 3.5,
            "bandwidth_mhz": 100,
            "tx_power_dbm": 46,
            "noise_figure_db": 7.0,
            "tx_gain_dbi": 18.0,
            "rx_gain_dbi": 0.0,
            "coverage_radius_m": 500,
            "ue_count": 20,
            "bs_height_m": 30,
            "ue_height_m": 1.5,
            "environment": "urban",
        }
    )

    def public_dict(self) -> dict:
        """对外暴露的配置（API Key 脱敏）。"""
        data = asdict(self)
        key = data.get("llm_api_key") or ""
        data["llm_api_key"] = (key[:4] + "…" + key[-4:]) if len(key) > 8 else ("已设置" if key else "")
        data["llm_api_key_set"] = bool(key)
        return data


settings = Settings()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_persisted_llm() -> None:
    """启动时读取页面保存过的模型配置。"""
    import json

    if not CONFIG_FILE.exists():
        return
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    for key in ("llm_mode", "llm_api_base", "llm_api_key", "llm_model", "llm_timeout", "llm_temperature"):
        if key in data and data[key] is not None:
            if key in ("llm_timeout", "llm_temperature"):
                setattr(settings, key, float(data[key]))
            else:
                setattr(settings, key, data[key])


def save_persisted_llm(payload: dict) -> None:
    """把模型配置写盘，重启后仍生效。"""
    import json

    current = {
        "llm_mode": settings.llm_mode,
        "llm_api_base": settings.llm_api_base,
        "llm_api_key": settings.llm_api_key,
        "llm_model": settings.llm_model,
        "llm_timeout": settings.llm_timeout,
        "llm_temperature": settings.llm_temperature,
    }
    for key in current:
        if key in payload and payload[key] is not None:
            if key in ("llm_timeout", "llm_temperature"):
                current[key] = float(payload[key])
            else:
                current[key] = payload[key]
    # 回写 settings
    for key, value in current.items():
        setattr(settings, key, value)
    CONFIG_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


load_persisted_llm()
