"""
UI Loader — 加载/切换 Snow UI Package。

主题目录: PROJECT_DIR/themes/installed/<主题名>/
用户下载主题 .zip 解压到该目录即可被识别。

依赖：ui_contract.py（契约声明）
不依赖：任何具体的 UI 文件路径
"""
from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from snow.paths import PROJECT_DIR
THEMES_DIR = PROJECT_DIR / "themes" / "installed"


class UILoader:
    """管理 UI Package 的加载（不负责 QWebChannel — 由 window.py 管理）。"""

    def __init__(self, webview: QWebEngineView):
        self._web = webview
        self._current = None
        self._manifests = {}

    # ── 公共 API ──

    def load(self, package_name: str) -> bool:
        """加载指定 UI package。返回是否成功。"""
        html_path = self._find_entry(package_name)
        if html_path is None:
            print(f"[UILoader] 主题不存在: {package_name}")
            return False

        # 用 setUrl 代替 setHtml — setHtml 在页面已有内容时
        # 会丢掉 QWebChannel 绑定，导致新主题 JS 连不上 bridge
        url = QUrl.fromLocalFile(str(html_path.resolve()))
        self._web.setUrl(url)
        self._current = package_name
        self._scan_manifests()
        return True

    def get_current(self) -> str | None:
        """返回当前加载的 UI package 名称。"""
        return self._current

    def list_ui(self) -> list[dict]:
        """返回所有已安装 UI package 的摘要。"""
        self._scan_manifests()
        result = []
        for name, mf in self._manifests.items():
            result.append({
                "name": name,
                "label": mf.get("label", name),
                "description": mf.get("description", ""),
                "version": mf.get("version", "?"),
            })
        current = self._current
        result.sort(key=lambda x: (0 if x["name"] == current else 1, x["label"]))
        return result

    # ── 内部 ──

    def _scan_dirs(self) -> list[Path]:
        """返回主题仓库目录。"""
        THEMES_DIR.mkdir(parents=True, exist_ok=True)
        return [THEMES_DIR]

    def _find_entry(self, package_name: str) -> Path | None:
        """在主题仓库中查找入口 HTML。"""
        pkg_dir = THEMES_DIR / package_name
        mf_path = pkg_dir / "manifest.json"
        if not mf_path.exists():
            return None
        try:
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            entry = mf.get("entry", "index.html")
            html_path = pkg_dir / entry
            if html_path.exists():
                return html_path
        except Exception:
            pass
        return None

    def _scan_manifests(self):
        """扫描主题仓库。"""
        self._manifests.clear()
        if not THEMES_DIR.exists():
            return
        for entry in THEMES_DIR.iterdir():
            if not entry.is_dir():
                continue
            mf_path = entry / "manifest.json"
            if not mf_path.exists():
                continue
            try:
                mf = json.loads(mf_path.read_text(encoding="utf-8"))
                self._manifests[entry.name] = mf
            except Exception:
                pass
