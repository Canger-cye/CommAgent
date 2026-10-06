# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    [r"C:/Users/Canger cye/Desktop/人工智能算法精英大赛/commagent/app_entry.py"],
    pathex=[r"C:/Users/Canger cye/Desktop/人工智能算法精英大赛/commagent"],
    binaries=[],
    datas=[
        (r"C:/Users/Canger cye/Desktop/人工智能算法精英大赛/commagent/frontend", "frontend"),
        (r"C:/Users/Canger cye/Desktop/人工智能算法精英大赛/commagent/demo_data", "demo_data"),
        (r"C:/Users/Canger cye/Desktop/人工智能算法精英大赛/commagent/docs", "docs"),
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
    hooksconfig={},
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
