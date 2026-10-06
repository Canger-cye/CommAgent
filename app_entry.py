"""CommAgent 桌面启动入口：开发 / PyInstaller 打包后均可双击运行。"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    """静态资源与代码根目录。"""
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _data_dir() -> Path:
    """可写数据目录（配置、输出）优先放 exe 旁，便携使用。"""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _ensure_path() -> Path:
    root = _resource_dir()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # 保证 backend 可导入
    parent = root if (root / "backend").exists() else root.parent
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    return parent


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) != 0


def _pick_port(host: str, start: int = 8787, tries: int = 20) -> int:
    port = start
    for _ in range(tries):
        if _port_free(host, port):
            return port
        port += 1
    return start


def main() -> None:
    _ensure_path()

    # 冻结后把可写目录指到 exe 旁
    os.environ.setdefault("COMMAGENT_DATA_DIR", str(_data_dir()))

    from backend.config import settings  # noqa: E402

    host = os.getenv("COMMAGENT_HOST", "127.0.0.1")
    port = int(os.getenv("COMMAGENT_PORT", "0")) or _pick_port(host, 8787)
    url = f"http://{host}:{port}"

    print("=" * 56)
    print("  CommAgent · 6G通感算智网络智能运维体")
    print(f"  模式 : {settings.llm_mode}")
    print(f"  地址 : {url}")
    print("  关闭本窗口即可退出程序")
    print("=" * 56)

    # 稍后打开浏览器
    def _open() -> None:
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()

    import uvicorn

    from backend.main import app

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
