"""Snow v3 Settings — sidebar + content panel, adapted for V3 paths."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QApplication, QComboBox, QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor
from pathlib import Path
import json, subprocess, sys

from snow.theme_manager import get_manager

PROJECT_DIR = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

# ── TTS engine (now embedded in V3) ──

# ── Colors (from ThemeManager) ──
def _c(key, default):
    return get_manager().get("settings", key, default)


def _f(s=12, b=False):
    for n in ["Microsoft YaHei", "SimHei", "Segoe UI"]:
        f = QFont(n, s); f.setBold(b)
        if f.family() == n: return f
    return QFont("Segoe UI", s)


class NavButton(QPushButton):
    _idx = 0

    def __init__(self, icon, text, parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self.setFont(_f(11))
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._update_style(False)

    def _update_style(self, active):
        bg = _c('nav_active_bg','rgba(100,180,160,0.15)') if active else "transparent"
        color = _c('accent','#64b4a0') if active else _c('text_dim','rgba(255,255,255,0.40)')
        self.setStyleSheet(
            f"QPushButton{{background:{bg};color:{color};border:none;"
            f"border-radius:8px;text-align:left;padding-left:12px;}}"
            f"QPushButton:hover{{background:{_c('nav_hover_bg','rgba(255,255,255,0.04)') if not active else _c('nav_active_bg','rgba(100,180,160,0.15)')};}}"
        )

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_style(checked)


class SettingsCenter(QWidget):
    voice_changed = Signal(str)
    model_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Snow \u8bbe\u7f6e")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(560, 400)

        self._nav_btns = []
        self._build()
        self._center()
        self._nav_btns[0].setChecked(True)

    def _center(self):
        geo = QApplication.primaryScreen().availableGeometry()
        self.move((geo.width() - self.width()) // 2,
                  (geo.height() - self.height()) // 2)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(_c('bg','#1e2a2a')))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)

    def _lbl(self, t, size=10, dim=False, bold=False):
        l = QLabel(t)
        l.setFont(_f(size, bold))
        c = _c('text_dim','rgba(255,255,255,0.40)') if dim else _c('text_primary','rgba(255,255,255,0.85)')
        l.setStyleSheet(f"color:{c};")
        l.setWordWrap(True)
        return l

    def _btn(self, t, accent=False, small=False):
        b = QPushButton(t)
        b.setFont(_f(10))
        b.setFixedHeight(26 if small else 30)
        b.setCursor(Qt.PointingHandCursor)
        c = _c('accent','#64b4a0') if accent else _c('btn_bg','rgba(255,255,255,0.08)')
        h = "rgba(100,180,160,0.4)" if accent else _c('btn_hover_bg','rgba(255,255,255,0.14)')
        tc = "#fff" if accent else _c('text_primary','rgba(255,255,255,0.85)')
        b.setStyleSheet(
            f"QPushButton{{background:{c};color:{tc};border:none;border-radius:6px;padding:0 14px;}}"
            f"QPushButton:hover{{background:{h};}}")
        return b

    def _combo(self):
        c = QComboBox()
        c.setFont(_f(11))
        c.setStyleSheet(f"""
            QComboBox{{background:{_c('input_bg','rgba(255,255,255,0.06)')};color:{_c('text_primary','rgba(255,255,255,0.85)')};border:none;border-radius:6px;padding:6px 10px;}}
            QComboBox::drop-down{{border:none;width:20px;}}
            QComboBox QAbstractItemView{{
                background:{_c('combo_dropdown_bg','#1a2828')};color:{_c('text_primary','rgba(255,255,255,0.85)')};border:none;
                selection-background:{_c('accent','#64b4a0')};outline:none;
            }}
        """)
        return c

    def _input(self, pw=False):
        i = QLineEdit()
        i.setFont(_f(11))
        if pw: i.setEchoMode(QLineEdit.Password)
        i.setStyleSheet(
            f"QLineEdit{{background:{_c('input_bg','rgba(255,255,255,0.06)')};color:{_c('text_primary','rgba(255,255,255,0.85)')};border:none;border-radius:6px;padding:7px 10px;}}"
            f"QLineEdit:focus{{background:{_c('input_focus_bg','rgba(255,255,255,0.10)')};}}")
        return i

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(140)
        sidebar.setStyleSheet(f"QFrame{{background:{_c('sidebar_bg','#162020')};border-radius:12px;}}")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(10, 14, 10, 10)
        sl.setSpacing(4)

        title = QLabel("  Snow")
        title.setFont(_f(14, True))
        title.setStyleSheet(f"color:{_c('text_primary','rgba(255,255,255,0.85)')};")
        sl.addWidget(title)
        sl.addSpacing(12)

        for icon, text in [("\U0001f916", "\u6a21\u578b"), ("\U0001f511", "\u5bc6\u94a5"), ("\U0001f50a", "\u8bed\u97f3"), ("\U0001f3a8", "\u4e3b\u9898"), ("\u2139\ufe0f", "\u5173\u4e8e")]:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, i=len(self._nav_btns): self._switch_page(i))
            self._nav_btns.append(btn)
            sl.addWidget(btn)

        sl.addStretch()
        ver = QLabel("Snow v3")
        ver.setFont(_f(9))
        ver.setStyleSheet(f"color:{_c('text_faint','rgba(255,255,255,0.20)')};padding-left:14px;")
        sl.addWidget(ver)
        outer.addWidget(sidebar)

        # ── Content area ──
        right = QFrame()
        right.setStyleSheet("QFrame{background:transparent;}")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 18, 18, 14)
        rl.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget{background:transparent;}")
        self._stack.addWidget(self._build_model_page())
        self._stack.addWidget(self._build_key_page())
        self._stack.addWidget(self._build_voice_page())
        self._stack.addWidget(self._build_theme_page())
        self._stack.addWidget(self._build_about_page())
        rl.addWidget(self._stack, 1)

        bb = QHBoxLayout()
        bb.addStretch()
        cb = self._btn("\u5173\u95ed", small=True)
        cb.clicked.connect(self.close)
        bb.addWidget(cb)
        rl.addLayout(bb)

        outer.addWidget(right, 1)

    def _switch_page(self, idx):
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        # 切到主题页时刷新列表
        if idx == 3 and hasattr(self, "_refresh_theme_list"):
            self._refresh_theme_list()
        # 切到关于页时刷新系统信息

    # ── Model page ──
    def _build_model_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(14)

        l.addWidget(self._lbl("AI \u6a21\u578b", size=14, bold=True))
        l.addWidget(self._lbl("\u9009\u62e9 Snow \u4f7f\u7528\u7684\u8bed\u8a00\u6a21\u578b", size=10, dim=True))
        l.addSpacing(4)

        self._model_cb = self._combo()
        self._load_models()
        self._model_cb.currentIndexChanged.connect(self._on_model_changed)
        l.addWidget(self._model_cb)

        self._model_status = self._lbl("", size=10, dim=True)
        l.addWidget(self._model_status)
        l.addSpacing(12)

        l.addWidget(self._lbl("\u6a21\u578b\u8bf4\u660e", size=11, bold=True))
        l.addWidget(self._lbl(
            "\u2601 DeepSeek V4 \u2014 \u4e91\u7aef\u6a21\u578b\uff0c\u901f\u5ea6\u5feb\u63a8\u7406\u5f3a\uff0c\u9700\u8054\u7f51",
            size=10, dim=True
        ))
        l.addStretch()
        return w

    def _load_models(self):
        cf = CONFIG_DIR / "model_config.json"
        try:
            if cf.exists():
                cfg = json.loads(cf.read_text(encoding="utf-8"))
                cur_model = cfg.get("model", "deepseek-v4-flash")
                for m in cfg.get("available_models", []):
                    self._model_cb.addItem(f"{m['name']} \u2014 {m['desc']} \u2601", m["id"])
                    if m["id"] == cur_model:
                        self._model_cb.setCurrentText(f"{m['name']} \u2014 {m['desc']} \u2601")
                return
        except Exception:
            pass
        self._model_cb.addItem("DeepSeek V4 Pro \u2014 \u6700\u5f3a\u63a8\u7406 \u2601", "deepseek-v4-pro")
        self._model_cb.addItem("DeepSeek V4 Flash \u2014 \u5feb\u901f\u54cd\u5e94 \u2601", "deepseek-v4-flash")

    def _on_model_changed(self, idx):
        self._save_model_config()
        self._model_status.setText("\u2713 \u5df2\u5207\u6362 \u2014 \u2601 \u4e91\u7aef\u6a21\u578b\uff0c\u9700\u8054\u7f51")
        self.model_changed.emit()

    def _save_model_config(self):
        idx = self._model_cb.currentIndex()
        mid = self._model_cb.itemData(idx) or "deepseek-v4-flash"
        cf = CONFIG_DIR / "model_config.json"
        cfg = {}
        if cf.exists():
            try:
                cfg = json.loads(cf.read_text(encoding="utf-8"))
            except Exception:
                pass
        provider = "deepseek"
        for m in cfg.get("available_models", []):
            if m["id"] == mid:
                provider = m.get("provider", "deepseek")
                break
        cfg["model"] = mid
        cfg["provider"] = provider
        CONFIG_DIR.mkdir(exist_ok=True)
        cf.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Key page ──
    def _build_key_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(14)

        l.addWidget(self._lbl("API \u5bc6\u94a5", size=14, bold=True))
        l.addWidget(self._lbl("DeepSeek API Key\uff0c\u4f7f\u7528\u4e91\u7aef\u6a21\u578b\u65f6\u9700\u8981", size=10, dim=True))
        l.addSpacing(4)

        self._key_in = self._input(pw=True)
        kf = CONFIG_DIR / "key.txt"
        if kf.exists():
            self._key_in.setText(kf.read_text(encoding="utf-8-sig").strip())
        self._key_in.setPlaceholderText("sk-... (DeepSeek API Key)")
        l.addWidget(self._key_in)

        kh = QHBoxLayout()
        kh.addWidget(self._lbl("\u5bc6\u94a5\u4fdd\u5b58\u5728\u672c\u5730 config/key.txt", size=10, dim=True))
        kh.addStretch()
        sk = self._btn("\u4fdd\u5b58", accent=True)
        sk.clicked.connect(self._save_key)
        kh.addWidget(sk)
        l.addLayout(kh)

        l.addSpacing(12)
        l.addWidget(self._lbl("\U0001f4a1 \u63d0\u793a", size=11, bold=True))
        l.addWidget(self._lbl(
            "\u672c\u5730\u6a21\u578b\uff08Qwen2.5\uff09\u4e0d\u9700\u8981 API Key\u3002\n"
            "\u5207\u6362\u6a21\u578b\u540e\u5bc6\u94a5\u4f1a\u81ea\u52a8\u4fdd\u7559\uff0c\u4e92\u4e0d\u5f71\u54cd\u3002",
            size=10, dim=True
        ))
        l.addStretch()
        return w

    def _save_key(self):
        k = self._key_in.text().strip()
        if k:
            CONFIG_DIR.mkdir(exist_ok=True)
            (CONFIG_DIR / "key.txt").write_text(k, encoding="utf-8")

    # ── Voice page ──
    def _build_voice_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(14)

        l.addWidget(self._lbl("\u8bed\u97f3 (TTS)", size=14, bold=True))
        l.addWidget(self._lbl("Snow \u6717\u8bfb\u56de\u590d\u65f6\u4f7f\u7528\u7684\u58f0\u97f3", size=10, dim=True))
        l.addSpacing(4)

        self._voice_cb = self._combo()
        voices = self._load_voices()
        self._voice_cb.addItems(voices)
        vf = DATA_DIR / "voice.txt"
        if vf.exists():
            cur = vf.read_text(encoding="utf-8").strip().split("\n")[0]
            if cur in voices:
                self._voice_cb.setCurrentText(cur)
        l.addWidget(self._voice_cb)

        vh = QHBoxLayout()
        vh.addStretch()
        tb = self._btn("\u8bd5\u542c")
        tb.clicked.connect(self._preview_voice)
        vh.addWidget(tb)
        sv = self._btn("\u4fdd\u5b58", accent=True)
        sv.clicked.connect(self._save_voice)
        vh.addWidget(sv)
        l.addLayout(vh)
        l.addSpacing(12)

        l.addWidget(self._lbl("\u53ef\u7528\u58f0\u97f3", size=11, bold=True))
        l.addWidget(self._lbl(" \u00b7 ".join(voices[:8]), size=10, dim=True))
        l.addStretch()
        return w

    def _load_voices(self):
        try:
            from snow.services._tts_engine import ALL_VOICES
            return list(ALL_VOICES)
        except Exception:
            return ["Xiaoxiao", "Yunxi", "Xiaoyi"]

    def _save_voice(self):
        v = self._voice_cb.currentText()
        DATA_DIR.mkdir(exist_ok=True)
        (DATA_DIR / "voice.txt").write_text(v, encoding="utf-8")
        self.voice_changed.emit(v)

    def _preview_voice(self):
        voice = self._voice_cb.currentText()
        if not voice:
            return
        btn = self.sender()
        if btn is not None:
            btn.setText("\u751f\u6210\u4e2d...")
            btn.setEnabled(False)
        QApplication.processEvents()
        try:
            from snow.services._tts_engine import _edge_generate, EDGE_VOICES, DEFAULT_VOICE
            from snow.services.tts import _player_cmd
            if voice not in EDGE_VOICES:
                voice = DEFAULT_VOICE
            wav = _edge_generate("\u4f60\u597d\uff0c\u8fd9\u662f Snow \u8bed\u97f3\u6d4b\u8bd5\u3002", voice)

            subprocess.Popen(
                _player_cmd(wav),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=0x08000000
            )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "TTS \u9519\u8bef", str(e))
        finally:
            if btn is not None:
                btn.setText("\u8bd5\u542c")
                btn.setEnabled(True)

    # ── Theme page ──

    def _build_theme_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(14)

        l.addWidget(self._lbl("\u4e3b\u9898", size=14, bold=True))
        l.addWidget(self._lbl("\u9009\u62e9 Snow \u7684 UI \u4e3b\u9898\u3002\u4e0d\u540c\u4e3b\u9898\u5171\u4eab\u540c\u6837\u7684 AI\u3001\u5929\u6c14\u3001\u5f85\u529e\u6570\u636e\uff0c\u53ea\u662f\u5448\u73b0\u65b9\u5f0f\u4e0d\u540c\u3002", size=10, dim=True))
        l.addSpacing(4)

        self._theme_btns = []
        self._theme_list = QWidget()
        tl = QVBoxLayout(self._theme_list)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(6)

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._theme_list)
        scroll.setFixedHeight(130)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:4px;background:transparent;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.08);border-radius:2px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setStyleSheet("background:transparent;")
        self._theme_list.setStyleSheet("background:transparent;")
        l.addWidget(scroll)
        l.addSpacing(4)

        l.addWidget(self._lbl("\U0001f4a1 \u63d0\u793a", size=11, bold=True))
        l.addWidget(self._lbl(
            "\u5207\u6362\u4e3b\u9898\u540e UI \u91cd\u65b0\u52a0\u8f7d\uff0cAI/\u8bb0\u5fc6/\u6570\u636e\u4fdd\u7559\u3002",
            size=10, dim=True
        ))
        l.addStretch()
        return w

    def _refresh_theme_list(self):
        # 清空旧按钮
        for b in self._theme_btns:
            b.setParent(None)
            b.deleteLater()
        self._theme_btns.clear()

        try:
            from snow.bridge import _bridge_instance
            if _bridge_instance:
                raw = _bridge_instance.get_ui_list()
                packages = json.loads(raw)
            else:
                packages = []
        except Exception:
            packages = []

        if not packages:
            return

        # 获取当前活跃主题
        current = "morandi"
        try:
            from snow.bridge import _bridge_instance
            if _bridge_instance and hasattr(_bridge_instance, "_ui_loader"):
                current = _bridge_instance._ui_loader.get_current() or "morandi"
        except Exception:
            pass

        tl = self._theme_list.layout()
        for pkg in packages:
            name = pkg.get("name", "")
            label = pkg.get("label", name)
            desc = pkg.get("description", "")
            is_active = (name == current)

            row = QWidget()
            row.setStyleSheet(
                f"QWidget{{background:{_c('nav_active_bg','rgba(100,180,160,0.15)') if is_active else 'transparent'};"
                f"border-radius:8px;padding:4px;}}"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 8, 10, 8)
            rl.setSpacing(10)

            symbol = "\u25c9" if is_active else "\u25cb"
            t = QLabel(f"{symbol}  {label}")
            t.setFont(_f(11, is_active))
            t.setStyleSheet(f"color:{_c('accent','#64b4a0') if is_active else _c('text_primary','rgba(255,255,255,0.85)')};background:transparent;")
            rl.addWidget(t, 1)

            if not is_active:
                apply_btn = self._btn("\u5e94\u7528", accent=True, small=True)
                apply_btn.clicked.connect(lambda checked, n=name: self._apply_theme(n))
                rl.addWidget(apply_btn)

            tl.addWidget(row)
            self._theme_btns.append(row)

    def _apply_theme(self, name: str):
        try:
            from snow.bridge import _bridge_instance
            if _bridge_instance:
                _bridge_instance.switch_ui(name)
        except Exception:
            pass
        self._refresh_theme_list()

    # ── About page ──
    def _build_about_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(14)

        l.addWidget(self._lbl("\u5173\u4e8e Snow", size=14, bold=True))
        l.addSpacing(4)
        l.addWidget(self._lbl("Snow v3", size=12, bold=True))
        l.addWidget(self._lbl("Windows \u684c\u9762 AI \u52a9\u624b", size=10, dim=True))
        l.addSpacing(6)
        l.addWidget(self._lbl(
            "\u57fa\u4e8e PySide6 + QWebEngine \u6784\u5efa\n"
            "AI \u5f15\u64ce\uff1aDeepSeek\n"
            "TTS\uff1aEdge TTS\n"
            "\u67b6\u6784\uff1a\u6a21\u5757\u5316\uff0c\u5de5\u5177\u6ce8\u518c\u8868\u81ea\u52a8\u6536\u96c6",
            size=10, dim=True
        ))
        l.addSpacing(12)
        l.addWidget(self._lbl("\u7cfb\u7edf\u4fe1\u606f", size=11, bold=True))
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            info = f"CPU: {cpu:.0f}%  \u00b7  \u5185\u5b58: {mem.percent:.0f}% ({mem.used//1024**3}/{mem.total//1024**3} GB)"
        except Exception:
            info = "\u65e0\u6cd5\u83b7\u53d6\u7cfb\u7edf\u4fe1\u606f"
        l.addWidget(self._lbl(info, size=10, dim=True))
        l.addStretch()
        return w
