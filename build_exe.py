# -*- coding: utf-8 -*-
"""PyInstaller 打包脚本：生成可双击运行的 CommAgent.exe。

用法：
  python build_exe.py
产物：
  dist/CommAgent/CommAgent.exe  （onedir，启动快、易分发）
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "CommAgent"
SPEC_NAME = "CommAgent.spec"


def build_spec_text() -> str:
    return f'''# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    [r"{(ROOT / "app_entry.py").as_posix()}"],
    pathex=[r"{ROOT.as_posix()}"],
    binaries=[],
    datas=[
        (r"{(ROOT / "frontend").as_posix()}", "frontend"),
        (r"{(ROOT / "demo_data").as_posix()}", "demo_data"),
        (r"{(ROOT / "docs").as_posix()}", "docs"),
    ],
    hiddenimports=[
        "backend",
        "backend.main",
        "backend.config",
        "backend.agents",
        "backend.agents.orchestrator",
        "backend.llm",
        "backend.llm.base",
        "backend.llm.fallback_chat",
        "backend.knowledge",
        "backend.knowledge.comm_knowledge",
        "backend.simulation",
        "backend.simulation.link_budget",
        "backend.simulation.beamforming",
        "backend.simulation.interference",
        "backend.simulation.network",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "anyio._backends._asyncio",
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CommAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CommAgent",
)
'''


def main() -> int:
    print("[build] 生成 Spec …")
    spec_path = ROOT / SPEC_NAME
    spec_path.write_text(build_spec_text(), encoding="utf-8")

    print("[build] PyInstaller 打包中（onedir）…")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        print("[build] 失败，退出码", proc.returncode)
        return proc.returncode

    exe = DIST / "CommAgent.exe"
    if not exe.exists():
        print("[build] 未找到", exe)
        return 2

    # 附带一键脚本与文档
    bat = DIST / "启动 CommAgent.bat"
    bat.write_text(
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "cd /d \"%~dp0\"\r\n"
        "start \"\" \"CommAgent.exe\"\r\n",
        encoding="utf-8",
    )
    readme = DIST / "使用说明.txt"
    readme.write_text(
        "CommAgent · 6G通感算智网络智能运维体\n"
        "====================================\n"
        "1. 双击「CommAgent.exe」或「启动 CommAgent.bat」\n"
        "2. 程序会自动打开浏览器控制台（若未打开，访问窗口里显示的地址）\n"
        "3. 右上角「模型设置」可切换本地演示 / 云端大模型\n"
        "4. 关闭黑色控制台窗口即退出软件\n"
        "5. 配置保存在本目录 outputs\\llm_config.json\n",
        encoding="utf-8",
    )

    # 复制完整源码包便于评审看代码（可选）
    src_keep = ["requirements.txt", "run.py", "README.md", "app_entry.py"]
    for name in src_keep:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, DIST / name)

    print("[build] 完成:", exe)
    print("[build] 目录:", DIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
