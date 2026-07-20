"""
Snow 路径管理 — 统一所有模块的路径解析。

开发模式：PROJECT_DIR = D:/snow_v4
打包模式（PyInstaller）：PROJECT_DIR = %APPDATA%/Snow/
  首次启动：从 sys._MEIPASS 复制默认配置到 APPDATA
"""
import os
import sys
import shutil
from pathlib import Path


def _get_project_dir() -> Path:
    """返回项目根目录。

    开发模式：main.py 所在目录
    PyInstaller 打包后：%APPDATA%/Snow/（首次自动从 _MEIPASS 迁移）
    """
    if getattr(sys, 'frozen', False):
        appdata = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
        return appdata / 'Snow'
    # 开发模式：找到 main.py 的父目录
    # snow/paths.py → snow/ → D:/snow_v4
    return Path(__file__).parent.parent


def _init_appdata():
    """PyInstaller 打包模式下，首次启动从 _MEIPASS 迁移默认文件到 APPDATA。

    规则：
    - 只创建不存在的目录/文件（不覆盖已有用户数据）
    - 迁移：config/ (不含key.txt), themes/, prompts/, assets/
    """
    if not getattr(sys, 'frozen', False):
        return  # 开发模式，不需要迁移

    meipass = Path(sys._MEIPASS)
    proj = PROJECT_DIR

    # 需要从 _MEIPASS 迁移的目录
    dirs_to_copy = ['themes', 'prompts', 'assets']
    # 需要迁移的 config 文件（不包括 key.txt，那是用户私密信息）
    config_files = ['model_config.json', 'ui.json']

    for dirname in dirs_to_copy:
        src = meipass / dirname
        dst = proj / dirname
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)

    config_dst = proj / 'config'
    config_dst.mkdir(parents=True, exist_ok=True)
    for fname in config_files:
        src = meipass / 'config' / fname
        dst = config_dst / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # 强制清除可能残留的 key.txt（旧版本打包 Bug）
    stale_key = config_dst / 'key.txt'
    if stale_key.exists():
        stale_key.unlink()

    data_dst = proj / 'data'
    data_dst.mkdir(parents=True, exist_ok=True)


PROJECT_DIR = _get_project_dir()
"""项目根目录 — 所有模块用它定位 themes/, config/, data/, prompts/ 等。

开发模式：D:/snow_v4
打包模式：%APPDATA%/Snow/
"""
