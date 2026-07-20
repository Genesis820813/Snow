"""World panel — desktop app icon grid with sorting and persistence."""
import os, json, subprocess
from pathlib import Path
from PySide6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from snow.paths import PROJECT_DIR


def cn_font(size=12, bold=False):
    for n in ["Microsoft YaHei", "SimHei", "Segoe UI"]:
        f = QFont(n, size)
        f.setBold(bold)
        if f.family() == n:
            return f
    return QFont("Segoe UI", size)


def _open_item(target: str):
    """打开目标：系统项（此电脑/回收站等带参数命令行）走 subprocess，
    普通路径走 os.startfile。"""
    if not target:
        return
    target = target.strip()
    try:
        # explorer.exe /e,::{CLSID} 等带参数的命令行，os.startfile 会抛 FileNotFoundError
        if " " in target and target.lower().startswith("explorer"):
            subprocess.Popen(target.split(), creationflags=0x08000000)
        else:
            os.startfile(target)
    except Exception:
        pass


_SYS_ORDER = {"\u6b64\u7535\u8111": 0, "\u56de\u6536\u7ad9": 1, "\u7f51\u7edc": 2, "\u63a7\u5236\u9762\u677f": 3}
_SYS_TOOLS = {"\u7535\u8111\u7ba1\u5bb6"}
COLORS = ["#1a73e8", "#e4405f", "#25d366", "#ff8c00", "#5c2d91", "#0088cc", "#ff4500", "#db4437"]


class WorldPanel:
    """Manages world panel icon rendering on a parent widget."""

    def __init__(self, parent, screen_w: int, screen_h: int, theme: str = ""):
        self._parent = parent
        self._open = False
        self._icons = []
        self._data = None
        self._file_items = []
        self._files_expanded = False
        self._sw = screen_w
        self._sh = screen_h
        self._theme = theme

        # Load cached data
        cache_file = PROJECT_DIR / "data" / "world_cache.json"
        if cache_file.exists():
            try:
                self._data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        self._create_button()

    def _create_button(self):
        self._btn = QPushButton("\u4e16\u754c", self._parent)
        self._btn.setFont(cn_font(14, True))
        self._btn.setFixedSize(130, 44)
        self._btn.move((self._sw - 130) // 2, 12)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet(
            "QPushButton{background:rgba(22,22,40,0.9);color:rgba(255,255,255,0.7);"
            "border-radius:22px;border:1px solid rgba(255,255,255,0.08);"
            "letter-spacing:6px;box-shadow:0 4px 12px rgba(0,0,0,0.3);}"
            "QPushButton:hover{box-shadow:0 4px 20px rgba(100,160,220,0.2);color:#fff;border-color:rgba(100,160,220,0.3);}"
        )
        s = QGraphicsDropShadowEffect(self._btn)
        s.setBlurRadius(30)
        s.setOffset(0, 8)
        s.setColor(QColor(0, 0, 0, 180))
        self._btn.setGraphicsEffect(s)
        self._btn.show()

    @property
    def button(self):
        return self._btn

    @property
    def is_open(self):
        return self._open

    def toggle(self):
        self._open = not self._open
        if self._open:
            if self._data:
                self._show(self._data.get("apps", []), self._data.get("files", []))
            self._btn.setStyleSheet(
                "QPushButton{background:rgba(100,160,220,0.25);color:#fff;"
                "border-radius:22px;border:1px solid rgba(100,160,220,0.3);"
                "letter-spacing:6px;box-shadow:0 4px 20px rgba(100,160,220,0.25);}"
            )
        else:
            for w in self._icons:
                w.hide(); w.setParent(None); w.deleteLater()
            self._icons.clear()
            self._btn.setStyleSheet(
                "QPushButton{background:rgba(22,22,40,0.9);color:rgba(255,255,255,0.7);"
                "border-radius:22px;border:1px solid rgba(255,255,255,0.08);"
                "letter-spacing:6px;box-shadow:0 4px 12px rgba(0,0,0,0.3);}"
                "QPushButton:hover{box-shadow:0 4px 20px rgba(100,160,220,0.2);color:#fff;border-color:rgba(100,160,220,0.3);}"
            )

    def set_theme(self, theme: str):
        self._theme = theme

    def show_icons(self, data_json: str):
        """Called by bridge when AI sends icon data."""
        self._open = True
        self._data = data_json
        data = json.loads(data_json) if isinstance(data_json, str) else data_json
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        (PROJECT_DIR / "data" / "world_cache.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        self._show(data.get("apps", []), data.get("files", []))
        self._btn.setStyleSheet(
            "QPushButton{background:rgba(100,160,220,0.25);color:#fff;"
            "border-radius:22px;border:1px solid rgba(100,160,220,0.3);"
            "letter-spacing:6px;box-shadow:0 4px 20px rgba(100,160,220,0.25);}"
        )

    def _show(self, apps, files):
        if self._theme == "morandi":
            self._show_left_right(apps, files)
            return
        btn_w, btn_h = 86, 32
        gap = 5
        per_col = 10
        left_margin = 20
        btn_y = 18

        def _sort_key(a):
            name = a.get("name", "").strip()
            if name in _SYS_ORDER:
                return (0, _SYS_ORDER[name], name)
            if name in _SYS_TOOLS:
                return (1, 0, name)
            if name.startswith("📄"):
                return (3, 0, name)
            return (2, 0, name)

        all_items = sorted(apps, key=_sort_key)
        for f_item in files:
            all_items.append({"name": f"📄 {f_item['name']}", "target": f_item["target"]})

        def _make_btn(name, target, x, y, i):
            color = COLORS[i % len(COLORS)]
            btn = QPushButton(self._parent)
            btn.setText(name[:9])
            btn.setFont(cn_font(10, True))
            btn.setFixedSize(btn_w, btn_h)
            btn.move(x, y)
            btn.setCursor(Qt.PointingHandCursor)
            s = QGraphicsDropShadowEffect(btn)
            s.setBlurRadius(14); s.setOffset(0, 3); s.setColor(QColor(0, 0, 0, 100))
            btn.setGraphicsEffect(s)
            btn.setStyleSheet(
                f"QPushButton{{background:rgba(22,22,40,0.9);color:rgba(255,255,255,0.5);"
                f"border-radius:10px;border:1px solid rgba(255,255,255,0.06);}}"
                f"QPushButton:hover{{color:#fff;border-color:{color};"
                f"background:rgba(30,30,50,0.95);}}"
            )
            btn.clicked.connect(lambda checked, t=target: _open_item(t))
            btn.show()
            self._icons.append(btn)

        for i, app in enumerate(all_items):
            col = i // per_col
            row = i % per_col
            x = left_margin + col * (btn_w + gap)
            y = btn_y + row * (btn_h + gap)
            _make_btn(app.get("name", "?"), app.get("target", ""), x, y, i)

    def _show_left_right(self, apps, files):
        """Apps laid out around world button: 5 per side per row (morandi theme)."""
        btn_w, btn_h = 76, 32
        gap = 6
        per_side = 5
        center_x = self._sw // 2
        world_btn_w = 130
        margin_to_btn = 14

        left_group_w = per_side * btn_w + (per_side - 1) * gap
        left_start_x = center_x - world_btn_w // 2 - margin_to_btn - left_group_w
        right_start_x = center_x + world_btn_w // 2 + margin_to_btn
        start_y = 66

        sorted_apps = sorted(apps, key=lambda a: (
            0 if a.get("name", "").strip() in _SYS_ORDER else 1,
            a.get("name", "").strip()
        ))

        # 文件和应用同流排列：都进左5右5的行式布局，不再单独一列
        items = list(sorted_apps)
        for f_item in files:
            items.append({
                "name": "📄 " + f_item.get("name", "?"),
                "target": f_item.get("target", ""),
                "_is_file": True,
            })

        for i, app in enumerate(items):
            name = app.get("name", "?")[:8]
            target = app.get("target", "")
            is_file = app.get("_is_file", False)
            row = i // (per_side * 2)
            pos = i % (per_side * 2)
            if pos < per_side:
                x = left_start_x + pos * (btn_w + gap)
            else:
                x = right_start_x + (pos - per_side) * (btn_w + gap)
            y = start_y + row * (btn_h + gap)
            btn = QPushButton(self._parent)
            btn.setText(name)
            btn.setFont(cn_font(10, True))
            btn.setFixedSize(btn_w, btn_h)
            btn.move(x, y)
            btn.setCursor(Qt.PointingHandCursor)
            s = QGraphicsDropShadowEffect(btn)
            s.setBlurRadius(10); s.setOffset(0, 2); s.setColor(QColor(90, 110, 100, 80))
            btn.setGraphicsEffect(s)
            if is_file:
                btn.setStyleSheet(
                    "QPushButton{background:rgba(66,78,70,0.88);color:rgba(215,228,210,0.92);"
                    "border-radius:8px;border:1px solid rgba(255,255,255,0.14);}"
                    "QPushButton:hover{background:rgba(96,115,102,0.95);color:#fff;"
                    "border-color:rgba(180,210,190,0.6);}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton{background:rgba(58,70,78,0.88);color:rgba(228,233,226,0.92);"
                    "border-radius:8px;border:1px solid rgba(255,255,255,0.14);}"
                    "QPushButton:hover{background:rgba(122,143,158,0.95);color:#fff;"
                    "border-color:rgba(200,220,210,0.6);}"
                )
            btn.clicked.connect(lambda checked, t=target: _open_item(t))
            btn.show()
            self._icons.append(btn)

    def clear(self):
        for w in self._icons:
            w.hide(); w.setParent(None); w.deleteLater()
        self._icons.clear()


