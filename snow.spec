# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Snow V4 — onedir build."""

import sys
from pathlib import Path

# 项目根目录
ROOT = Path(r"D:\snow_v4")

# ── 收集数据文件 ──
def _collect_dir(rel_path: str) -> list[tuple[str, str]]:
    """递归收集目录下的所有文件，返回 [(src, dst_dir), ...]"""
    src_dir = ROOT / rel_path
    if not src_dir.exists():
        return []
    results = []
    for f in src_dir.rglob("*"):
        if f.is_file():
            dst = str(f.relative_to(ROOT).parent)
            results.append((str(f), dst))
    return results

datas = []
# 主题（Web UI）
datas += _collect_dir("themes")
# 配置文件模板（不含 key.txt——那是用户私密）
datas += [(str(ROOT / "config" / "model_config.json"), "config")]
datas += [(str(ROOT / "config" / "ui.json"), "config")]
# Prompt 模板
datas += _collect_dir("prompts")
# 图标资源
datas += _collect_dir("assets")
# 初始数据目录（只保留结构，去掉缓存文件）
for f in (ROOT / "data").rglob("*"):
    if f.is_file():
        # 只打包初始模板文件，不含用户缓存
        if f.name in ("voice.txt",):
            datas.append((str(f), str(f.relative_to(ROOT).parent)))

# ── 隐藏导入 ──
hiddenimports = [
    # Qt
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngine",
    "PySide6.QtWebChannel",
    "PySide6.QtMultimedia",
    "PySide6.QtNetwork",
    # Windows COM
    "pythoncom",
    "win32com",
    "win32com.client",
    "win32com.shell",
    # Snow 内部模块
    "snow",
    "snow.agent",
    "snow.bridge",
    "snow.window",
    "snow.paths",
    "snow.theme_manager",
    "snow.ui_loader",
    "snow.scanner",
    "snow.classify",
    "snow.prompt",
    "snow.settings",
    "snow.ui_contract",
    "snow.panels",
    "snow.panels.world",
    "snow.panels.left_card",
    "snow.panels.right_card",
    "snow.widgets",
    "snow.widgets.logo",
    "snow.widgets.glass_card",
    "snow.tools",
    "snow.tools.app",
    "snow.tools.classify",
    "snow.tools.desktop",
    "snow.tools.document",
    "snow.tools.file",
    "snow.tools.registry",
    "snow.tools.snow",
    "snow.tools.system",
    "snow.tools.web",
    "snow.tools.world",
    "snow.services",
    "snow.services._edge_tts_worker",
    "snow.services._hotsearch_legacy",
    "snow.services._tts_engine",
    "snow.services.hotsearch",
    "snow.services.memory",
    "snow.services.monitor",
    "snow.services.todos",
    "snow.services.tts",
    "snow.services.weather",
    "snow.services.worklog",
    # 依赖
    "psutil",
    "PIL",
    "docx",
    "openpyxl",
    "edge_tts",
]

# ── 排除不必要的模块 ──
excludes = [
    "tkinter",
    "unittest",
    "test",
    "pydoc",
    "distutils",
    "setuptools",
    "pip",
    "wheel",
    "pkg_resources",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "jedi",
    "IPython",
    "jupyter",
    "notebook",
    "sphinx",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Snow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "snow.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Snow",
)
