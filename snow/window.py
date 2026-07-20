"""Snow v3 Window — transparent fullscreen overlay with modular panels."""
import sys, ctypes, json, os
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu,
    QPushButton, QGraphicsDropShadowEffect, QLineEdit,
    QTextEdit, QHBoxLayout, QVBoxLayout,
)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QThreadPool, QRunnable, QObject
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QPainterPath,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
from PySide6.QtCore import QUrl

from snow.theme_manager import get_manager as get_theme

from snow.paths import PROJECT_DIR
THEMES_DIR = PROJECT_DIR / "themes" / "installed"


def adaptive_chat_size(sw: int, sh: int) -> tuple:
    """对话框自适应尺寸：跟随屏幕宽高按比例算，带上下限。
    任何分辨率下（1366x768 老笔记本到 4K）都得体。"""
    w = max(520, min(780, int(sw * 0.55)))
    h = max(300, min(360, int(sh * 0.40)))
    return w, h

# Win32 helpers
WM_NCHITTEST = 0x0084
WM_HOTKEY = 0x0312
HTTRANSPARENT = -1

class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_ulonglong),
        ("lParam", ctypes.c_longlong),
        ("time", ctypes.c_uint),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]

MORANDI_TOP = QColor("#7a8f9e")
MORANDI_BOT = QColor("#58695e")


def cn_font(size=12, bold=False):
    for n in ["Microsoft YaHei", "SimHei", "Segoe UI"]:
        f = QFont(n, size)
        f.setBold(bold)
        if f.family() == n:
            return f
    return QFont("Segoe UI", size)


class TransparentDialog(QWidget):
    """Independent top-level dialog — floats above WorkerW-embedded window.

    Must NOT pass extra args to QWidget.__init__ (only optional parent).
    """

    def __init__(self, bridge, sw, sh, parent=None):
        # QWidget only accepts (parent=None); never pass bridge/sw/sh to super().
        super().__init__(parent)
        self._bridge = bridge
        self._sw = sw
        self._sh = sh
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, sw, sh)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self._chat = QTextEdit(self)
        self._chat.setReadOnly(True)
        self._chat.setStyleSheet(
            "QTextEdit{background:rgba(0,0,0,0.18);color:rgba(255,255,255,0.78);"
            "border:none;border-radius:12px;padding:14px 18px;font-size:14px;"
            "font-family:'Noto Sans SC';line-height:1.7;}"
        )
        self._chat_w = max(480, min(740, int(self._sw * 0.52)))
        self._chat.setFixedWidth(self._chat_w)
        self._chat.setMinimumHeight(60)
        self._chat.setMaximumHeight(self._sh - 150)
        self._chat.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chat.hide()

        self._bar = QWidget(self)
        self._bar.setStyleSheet(
            "background:rgba(18,18,32,0.65);border-radius:28px;"
            "border:1px solid rgba(255,255,255,0.06);"
        )
        self._bar.setFixedHeight(46)
        layout = QHBoxLayout(self._bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        def _btn(text, color="rgba(255,255,255,0.4)"):
            b = QPushButton(text, self._bar)
            b.setFixedSize(34, 34)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:rgba(255,255,255,0.06);color:{color};"
                f"border:none;border-radius:17px;font-size:14px;}}"
                f"QPushButton:hover{{background:rgba(255,255,255,0.16);color:#fff;}}"
            )
            return b

        add_btn = _btn("＋")
        add_btn.clicked.connect(lambda: self._bridge.pick_file() if hasattr(self._bridge, 'pick_file') else None)
        layout.addWidget(add_btn)

        set_btn = _btn("⚙")
        set_btn.clicked.connect(lambda: self._bridge.open_settings() if hasattr(self._bridge, 'open_settings') else None)
        layout.addWidget(set_btn)

        self._input = QLineEdit(self._bar)
        self._input.setPlaceholderText("type...")
        self._input.setStyleSheet(
            "QLineEdit{background:transparent;border:none;color:rgba(255,255,255,0.75);"
            "font-size:13px;font-family:'Noto Sans SC';padding:0 6px;}"
        )
        self._input.returnPressed.connect(self._send)
        layout.addWidget(self._input, 1)

        tts_btn = _btn("S", "rgba(200,240,220,0.85)")
        tts_btn.clicked.connect(lambda: self._bridge.toggle_tts())
        layout.addWidget(tts_btn)

        send_btn = _btn(">", "rgba(220,240,230,0.85)")
        send_btn.clicked.connect(self._send)
        layout.addWidget(send_btn)

        self._sub_btn = _btn("sub")
        self._sub_btn.setFixedSize(44, 34)
        self._sub_btn.clicked.connect(self._toggle_chat)
        layout.addWidget(self._sub_btn)

        self._bar.hide()

        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(30, 30)
        self._close_btn.move(self._sw - 46, 14)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(
            "QPushButton{background:rgba(220,50,50,0.6);color:rgba(255,255,255,0.7);"
            "border:none;border-radius:15px;font-size:13px;}"
            "QPushButton:hover{background:rgba(220,50,50,0.9);color:#fff;}"
        )
        self._close_btn.clicked.connect(self._exit)
        self._close_btn.hide()

        self._position_widgets()

    def _position_widgets(self):
        bar_w = max(420, min(600, int(self._sw * 0.45)))
        bar_y = self._sh - 58
        self._bar.setGeometry((self._sw - bar_w)//2, bar_y, bar_w, 46)
        doc_h = int(self._chat.document().size().height()) + 30
        max_h = self._sh // 2
        h = max(min(doc_h, max_h), 60)
        chat_bottom = bar_y - 14
        self._chat.setGeometry((self._sw - self._chat_w)//2, chat_bottom - h, self._chat_w, h)

    def _connect_signals(self):
        self._bridge.ai_token.connect(self._on_token)
        self._bridge.ai_done.connect(self._on_done)
        self._bridge.exit_requested.connect(self._on_exit_requested)

    def _on_token(self, text):
        self._chat.insertPlainText(text)
        self._chat.ensureCursorVisible()
        self._resize_chat()
        self._chat.repaint()

    def _resize_chat(self):
        doc_h = int(self._chat.document().size().height()) + 30
        bar_y = self._sh - 58
        max_h = self._sh // 2
        h = max(min(doc_h, max_h), 60)
        chat_bottom = bar_y - 14
        self._chat.setGeometry((self._sw - self._chat_w)//2, chat_bottom - h, self._chat_w, h)
        if doc_h > max_h:
            self._chat.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self._chat.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def _on_done(self, full):
        self._chat.append("")
        self._resize_chat()
        self._chat.repaint()
        if full and full.strip():
            self._bridge.speak(full)

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._chat.append(
            f'<div style="text-align:right;color:rgba(180,210,200,0.70);margin:4px 0;">{text}</div>'
        )
        self._bridge.ask(text)

    def _toggle_chat(self):
        v = self._chat.isVisible()
        self._chat.setVisible(not v)

    def _exit(self):
        """✕ 按钮：隐藏自己并请求全局退出（只发一次信号）。"""
        self.hide()
        self._bridge.exit_requested.emit()

    def _on_exit_requested(self):
        """收到全局退出信号：只隐藏，绝不再 emit——防信号自递归。"""
        self.hide()

    def show_dialog(self):
        self._chat.clear()
        self._resize_chat()
        self._chat.show()
        self._bar.show()
        self._close_btn.show()
        self.show()
        self._input.setFocus()
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            f.write("[dialog] show_dialog called\n")

    def hide_dialog(self):
        self._chat.hide()
        self._bar.hide()
        self._close_btn.hide()
        self.hide()


class SnowWindow(QWidget):
    _cards_ready = Signal(object, object)  # (weather_data_or_none, hotsearch_items_or_none)

    def __init__(self, diag=False, first_setup=False):
        super().__init__()
        self._diag = diag
        self._first_setup = first_setup
        self._card_fetching = False  # 防止慢请求时定时器堆积多个后台任务
        self._cards_ready.connect(self._on_cards_ready)
        self.setWindowTitle("Snow")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool
        )
        self.setAutoFillBackground(True)

        # ── 主题模式早判定：chat_only = 真·独立对话框，不创建任何 morandi 组件 ──
        self._minimal_mode = False
        self._active_theme = "morandi"
        try:
            _cfg_file = PROJECT_DIR / "config" / "ui.json"
            if _cfg_file.exists():
                _start = json.loads(_cfg_file.read_text(encoding="utf-8")).get("active", "morandi")
                self._active_theme = _start  # 世界面板等组件创建时就要用对的主题名
                self._minimal_mode = self._get_theme_mode(_start) == "chat_only"
        except Exception:
            pass

        # ── Video background ──
        self._video_frame = None  # QPixmap，预缩放后的最新视频帧
        self._video_config = None
        self._video_embedded = False
        self._transparent_embedded = False
        self._trans_dialog = None  # TransparentDialog, lazy-created

        self._embed_epoch = 0  # 嵌入定时器竞争防护
        if not self._minimal_mode:
            self._video_sink = QVideoSink(self)
            self._video_sink.videoFrameChanged.connect(self._on_video_frame)
            self._media_player = QMediaPlayer(self)
            self._media_player.setVideoSink(self._video_sink)
            self._media_player.setLoops(QMediaPlayer.Infinite)
            self._media_player.mediaStatusChanged.connect(self._on_video_status)

        geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(geo)
        self._sw = geo.width()
        self._sh = geo.height()

        from snow.bridge import SnowBridge
        self._bridge = SnowBridge()
        self._bridge._parent_window = self
        self._bridge.exit_requested.connect(self.exit_snow)
        self._bridge.ai_work.connect(self._on_ai_work)
        self._bridge.todos_changed.connect(self._on_todos_changed)
        self._bridge.world_toggle.connect(self._toggle_world)
        self._bridge.world_show.connect(self._on_world_show)

        if not self._minimal_mode:
            self._setup_logo()
            self._setup_world()
            self._setup_cards()
            self._setup_close_button()
        self._setup_tray()
        self._setup_webview()

        self._push_to_bottom()
        # chat_only 极简模式：桌面必须原样保留——不藏图标，反而主动恢复（防上次异常退出残留）
        if self._get_theme_mode(getattr(self, "_active_theme", "")) == "chat_only":
            try:
                self._show_desktop_icons()
            except Exception:
                pass
        else:
            self._safe_hide_icons()

        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [window] init complete, auto-greet in 2.5s\n")
        QTimer.singleShot(2500, self._auto_greet)
        # 首次运行：自动打开设置页面让用户配置模型和API Key
        if self._first_setup:
            QTimer.singleShot(1500, self._open_settings_for_first_run)

    # ── nativeEvent (hotkey + video mouse passthrough) ──

    def nativeEvent(self, eventType, message):
        """统一处理：ESC 热键退出 + 视频模式控件外鼠标穿透。"""
        if eventType != b"windows_generic_MSG":
            return False, 0
        msg = _MSG.from_address(int(message))

        # 视频模式：控件外鼠标穿透到桌面图标
        if self._video_config and msg.message == WM_NCHITTEST:
            pt_x = ctypes.c_short(msg.lParam & 0xFFFF).value  # 有符号：兼容多屏负坐标
            pt_y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
            wp = self.mapFromGlobal(QPoint(pt_x, pt_y))
            in_web = hasattr(self, '_web') and self._web.geometry().contains(wp)
            in_close = hasattr(self, '_close_btn') and self._close_btn and self._close_btn.geometry().contains(wp)
            if in_web or in_close:
                return False, 0
            return True, HTTRANSPARENT

        return False, 0

    # ── Background ──

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 视频模式：画预缩放帧（性能优化：paintEvent 内不做 scaled）
        if self._video_config and self._video_frame and not self._video_frame.isNull():
            p.drawPixmap(self.rect(), self._video_frame)
            p.end()
            return
        elif self._video_config:
            # 视频激活但还没第一帧——画黑底
            p.fillRect(self.rect(), QColor(0, 0, 0))
            p.end()
            return

        tm = get_theme()
        top_str = tm.get("background", "top", "#7a8f9e")
        bot_str = tm.get("background", "bottom", "#58695e")

        if top_str == "transparent" or bot_str == "transparent":
            wp_path = THEMES_DIR / getattr(self, '_active_theme', 'red-ribbon') / "红丝带壁纸.png"
            if wp_path.exists():
                pm = QPixmap(str(wp_path.resolve()))
                if not pm.isNull():
                    p.drawPixmap(self.rect(), pm.scaled(self._sw, self._sh, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            p.end()
            return

        top_c = QColor(top_str)
        bot_c = QColor(bot_str)
        ratio = tm.get("background", "split_ratio", 0.4)

        ly = int(self._sh * (1.0 - ratio))
        ry = int(self._sh * ratio)
        p.fillRect(self.rect(), bot_c)
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(self._sw, 0)
        path.lineTo(self._sw, ry)
        path.lineTo(0, ly)
        path.closeSubpath()
        p.fillPath(path, top_c)
        p.end()

    # ── Video ──

    def _on_video_status(self, status):
        if status == QMediaPlayer.LoadedMedia:
            self._media_player.play()
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                import time
                f.write(f"{time.strftime('%H:%M:%S')} [Video] loaded, playing\n")
        elif status == QMediaPlayer.InvalidMedia:
            print("[Video] Invalid media — stopping", flush=True)
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                import time
                f.write(f"{time.strftime('%H:%M:%S')} [Video] INVALID MEDIA\n")
            self._stop_video()
        elif status == QMediaPlayer.NoMedia:
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                import time
                f.write(f"{time.strftime('%H:%M:%S')} [Video] NoMedia\n")

    def _on_video_frame(self, frame):
        """捕获视频帧，预缩放 + 帧率限制（15fps）避免 UI 线程卡死。"""
        if not frame.isValid():
            return
        # 帧率限制：最多 15fps
        import time
        now = time.time()
        if not hasattr(self, '_last_frame_ts'):
            self._last_frame_ts = 0
        if now - self._last_frame_ts < 1.0 / 15:
            return
        self._last_frame_ts = now

        img = frame.toImage()
        if not img.isNull():
            # 预缩放到窗口尺寸，paintEvent 直接 drawPixmap
            self._video_frame = QPixmap.fromImage(img).scaled(
                self._sw, self._sh, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.update()

        # 每 2 秒记一次日志
        if not hasattr(self, '_last_frame_log') or now - self._last_frame_log > 2:
            self._last_frame_log = now
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} [Video] frame valid={frame.isValid()}, "
                        f"pixmap_null={self._video_frame.isNull() if self._video_frame else 'N/A'}\n")

    def _start_video(self, video_cfg):
        if not hasattr(self, '_media_player'):
            return  # chat_only 极简模式：无视频机件
        self._video_config = video_cfg
        video_file = video_cfg.get("file", "") if isinstance(video_cfg, dict) else video_cfg
        video_path = THEMES_DIR / self._active_theme / video_file
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [Video] _start_video: file={video_file}, "
                    f"exists={video_path.exists()}, path={video_path}\n")
        if not video_path.exists():
            print(f"[Video] file not found: {video_path}", flush=True)
            self._stop_video()
            return

        self._media_player.setSource(QUrl.fromLocalFile(str(video_path.resolve())))
        self.update()

        # 2 秒后嵌入 WorkerW（带 epoch，主题切走则作废）
        _ep = getattr(self, '_embed_epoch', 0)
        QTimer.singleShot(2000, lambda: self._embed_to_desktop(_ep))

    def _embed_to_desktop(self, epoch=None):
        """Snow 窗口嵌入 WorkerW 空层——窗口变壁纸，图标浮在上面。"""
        # 防定时器竞争：若排定后主题已切走（epoch 变化），放弃嵌入
        if epoch is not None and epoch != getattr(self, "_embed_epoch", 0):
            return
        if self._video_embedded or self._transparent_embedded:
            return
        try:
            user32 = ctypes.windll.user32

            # 1. 触发 Progman 生成空 WorkerW
            progman = user32.FindWindowW("Progman", None)
            if progman:
                user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 0, None)

            # 2. 找空 WorkerW
            target = ctypes.c_void_p(0)
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def _find_empty(hwnd, _):
                nonlocal target
                cn = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cn, 256)
                if cn.value != "WorkerW":
                    return True
                if not user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None):
                    target = ctypes.c_void_p(hwnd)
                    return False
                return True

            user32.EnumWindows(WNDENUMPROC(_find_empty), 0)

            if target.value:
                hwnd = int(self.winId())
                user32.SetParent(hwnd, target.value)
                # 去掉 WS_CHILD，设 WS_POPUP — WorkerW 不转发输入给子窗口
                GWL_STYLE = -16
                WS_CHILD = 0x40000000
                WS_POPUP = 0x80000000
                style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                user32.SetWindowLongW(hwnd, GWL_STYLE, (style & ~WS_CHILD) | WS_POPUP)
                self.setGeometry(0, 0, self._sw, self._sh)
                if self._video_config:
                    self._video_embedded = True
                else:
                    self._transparent_embedded = True
                self._show_desktop_icons()
                if hasattr(self, '_web') and self._web.isVisible():
                    self._web.setFocus()
                # 强制窗口获取输入焦点（WorkerW 内）
                user32.SetFocus(hwnd)
                # 顶层对话框独立于 WorkerW，负责输入
                if self._trans_dialog is not None:
                    self._trans_dialog.raise_()
                    if hasattr(self._trans_dialog, '_input'):
                        self._trans_dialog._input.setFocus()
                if hasattr(self, '_close_btn') and self._close_btn and self._close_btn.isVisible():
                    self._close_btn.raise_()
                with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                    import time
                    f.write(f"{time.strftime('%H:%M:%S')} [Video] embedded {target.value:#x}\n")
            else:
                with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                    import time
                    f.write(f"{time.strftime('%H:%M:%S')} [Video] no empty WorkerW\n")
        except Exception as e:
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                import time
                f.write(f"{time.strftime('%H:%M:%S')} [Video] embed error: {e}\n")

    def _stop_video(self):
        self._embed_epoch = getattr(self, '_embed_epoch', 0) + 1  # 作废未触发的嵌入定时器
        if hasattr(self, '_media_player'):
            self._media_player.stop()
            self._media_player.setSource(QUrl())
        self._video_frame = None
        self._video_config = None
        # 解嵌
        if self._video_embedded or self._transparent_embedded:
            try:
                ctypes.windll.user32.SetParent(int(self.winId()), 0)
            except Exception:
                pass
            self._video_embedded = False
            self._transparent_embedded = False
        self._hide_desktop_icons()
        self.update()

    def _video_config_for(self, package_name):
        mf_path = THEMES_DIR / package_name / "manifest.json"
        if not mf_path.exists():
            return None
        try:
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            return mf.get("video")
        except Exception:
            return None

    # ── Logo ──

    def _setup_logo(self):
        from snow.widgets.logo import LogoWidget
        self._logo = LogoWidget(self)
        self._logo.move((self._sw - 200) // 2, (self._sh - 200) // 2)
        self._logo.show()

    # ── World panel ──

    def _setup_world(self):
        from snow.panels.world import WorldPanel
        self._world = WorldPanel(self, self._sw, self._sh, theme=getattr(self, "_active_theme", ""))
        self._world.button.clicked.connect(self._toggle_world)

    def _on_world_show(self, data):
        if not hasattr(self, '_world'):
            return
        self._world.show_icons(data)

    def _toggle_world(self):
        if not hasattr(self, '_world'):
            return
        self._world.toggle()
        # chat_only 模式：动态调整 WebView 给世界图标让位
        if self._get_theme_mode(self._active_theme) == "chat_only":
            if self._world.is_open:
                icon_count = len(self._world._icons)
                rows = max(1, (icon_count + 9) // 10) if icon_count else 1
                icon_area = 18 + rows * 37 + 12  # y起点 + 行高 + 留白
                web_y = max(56, icon_area)
                self._web.setGeometry(0, web_y, self._sw, self._sh - web_y)
            else:
                self._web.setGeometry(0, 0, self._sw, self._sh)
                self._web.setFocus()

    # ── Cards ──

    def _setup_cards(self):
        from snow.widgets.glass_card import GlassCard
        from snow.panels.left_card import LeftCard
        from snow.panels.right_card import RightCard

        card_w, card_h = 260, 380
        margin = 22
        bottom_y = self._sh - card_h - 120

        self._left_frame = GlassCard(self, card_w, card_h)
        self._left_frame.move(margin, bottom_y)
        self._left_frame.show()
        self._left_card = LeftCard(self._left_frame)
        self._left_frame._card = self._left_card

        self._right_frame = GlassCard(self, card_w, card_h)
        self._right_frame.move(self._sw - card_w - margin, bottom_y)
        self._right_frame.show()
        self._right_card = RightCard(self._right_frame, on_todo_click=self._on_todo_click)

        self._card_timer = QTimer(self)
        self._card_timer.timeout.connect(self._refresh_cards)
        self._card_timer.start(15000)
        QTimer.singleShot(500, self._refresh_cards)

    def _refresh_cards(self):
        """后台线程拉取天气+热搜，完成后经信号回主线程刷卡片。"""
        if self._card_fetching:
            return  # 上一轮还在跑，跳过这轮避免堆积
        self._card_fetching = True
        class _CardsRunnable(QRunnable):
            def __init__(self, win):
                super().__init__()
                self._win = win
            def run(self):
                w_data = None
                h_data = None
                try:
                    w_raw = self._win._bridge.get_weather()
                    w_data = json.loads(w_raw) if w_raw else None
                except Exception:
                    pass
                try:
                    h_raw = self._win._bridge.get_hotsearch()
                    h_data = json.loads(h_raw) if h_raw else None
                except Exception:
                    pass
                self._win._cards_ready.emit(w_data, h_data)
        QThreadPool.globalInstance().start(_CardsRunnable(self))

    def _on_cards_ready(self, w_data, h_data):
        """主线程接收后台数据并刷新左右卡片。"""
        self._card_fetching = False
        self._apply_card_data(w_data, h_data)
        try:
            todos = json.loads(self._bridge.get_todos())
            self._right_card.render_todos(todos)
        except Exception:
            pass

    def _apply_card_data(self, w_data, h_data):
        if w_data:
            self._left_card.set_weather(w_data)
        if h_data:
            self._left_card.set_hotsearch(h_data)

    def _on_ai_work(self, label):
        if not hasattr(self, '_right_card'):
            return
        self._right_card.append_work(label)

    def _on_todos_changed(self):
        if not hasattr(self, '_right_card'):
            return
        try:
            todos = json.loads(self._bridge.get_todos())
            self._right_card.render_todos(todos)
        except Exception:
            pass

    def _on_todo_click(self, idx):
        self._bridge.toggle_todo(idx)
        self._on_todos_changed()

    # ── Close button ──

    def _setup_close_button(self):
        tm = get_theme()
        btn = QPushButton("\u2715", self)
        btn.setFixedSize(30, 30)
        btn.move(self._sw - 46, self._sh - 46)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{background:{tm.get('close_button','bg','rgba(255,255,255,0.05)')};"
            f"color:{tm.get('close_button','text','rgba(255,255,255,0.20)')};"
            f"border:none;border-radius:15px;font-size:13px;}}"
            f"QPushButton:hover{{background:{tm.get('close_button','hover_bg','rgba(220,50,50,0.3)')};"
            f"color:{tm.get('close_button','hover_text','#ffffff')};}}"
        )
        btn.clicked.connect(self.exit_snow)
        self._close_btn = btn
        btn.show()



    def _setup_webview(self):
        self._web = QWebEngineView(self)
        self._web.setContextMenuPolicy(Qt.NoContextMenu)

        web_w, web_h = adaptive_chat_size(self._sw, self._sh)
        web_x = (self._sw - web_w) // 2
        web_y = self._sh - web_h - 4
        self._web.setGeometry(web_x, web_y, web_w, web_h)
        self._web.raise_()
        self._web.page().setBackgroundColor(Qt.transparent)

        from PySide6.QtWebEngineCore import QWebEngineSettings
        self._web.settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)

        from PySide6.QtWebChannel import QWebChannel
        self._channel = QWebChannel()
        self._channel.registerObject("snow", self._bridge)

        from snow.ui_loader import UILoader
        self._ui_loader = UILoader(self._web)
        self._bridge._ui_loader = self._ui_loader

        config_file = PROJECT_DIR / "config" / "ui.json"
        start_theme = "morandi"
        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text(encoding="utf-8"))
                start_theme = cfg.get("active", "morandi")
            except Exception:
                pass

        self._web.page().setWebChannel(self._channel)
        self._ui_loader.load(start_theme)
        self._active_theme = start_theme

        get_theme().load(start_theme)

        mf = self._video_config_for(start_theme)
        if mf:
            self._start_video(mf)

        self._sync_transparent_ui(start_theme)
        self.update()

        self._web.setFocusPolicy(Qt.StrongFocus)
        self._web.setFocus()

        self._web.page().renderProcessTerminated.connect(self._on_render_crashed)

    def _on_render_crashed(self, status):
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [window] render process crashed (status={status}), reloading...\n")
        current = self._ui_loader.get_current() or "morandi"
        from PySide6.QtWebChannel import QWebChannel
        self._channel = QWebChannel()
        self._channel.registerObject("snow", self._bridge)
        self._web.page().setWebChannel(self._channel)
        self._ui_loader.load(current)
        # 崩溃重载后恢复当前主题的几何/可见性（极简窗口尺寸、组件显隐）
        try:
            self._sync_transparent_ui(current)
        except Exception:
            pass

    def switch_ui(self, package_name: str):
        if not hasattr(self, "_ui_loader") or self._ui_loader is None:
            from snow.ui_loader import UILoader
            self._ui_loader = UILoader(self._web)
            self._bridge._ui_loader = self._ui_loader
        from PySide6.QtWebChannel import QWebChannel
        self._channel = QWebChannel()
        self._channel.registerObject("snow", self._bridge)
        self._web.page().setWebChannel(self._channel)
        ok = self._ui_loader.load(package_name)
        if ok:
            # ── 结构性切换检测：chat_only ↔ 普通主题必须整进程重启 ──
            # 两种模式创建的组件完全不同（极简不建卡片/世界/视频），热切必然串味。
            new_minimal = self._get_theme_mode(package_name) == "chat_only"
            if new_minimal != getattr(self, "_minimal_mode", False):
                config_file = PROJECT_DIR / "config" / "ui.json"
                config_file.parent.mkdir(exist_ok=True)
                config_file.write_text(
                    json.dumps({"active": package_name}, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                    import time
                    f.write(f"{time.strftime('%H:%M:%S')} [window] structural theme switch "
                            f"-> {package_name}, restarting Snow\n")
                import subprocess
                # 打包模式下 sys.executable 就是 Snow.exe，直接启动即可
                if getattr(sys, 'frozen', False):
                    subprocess.Popen(
                        [sys.executable, "--wait-pid", str(os.getpid())],
                        cwd=str(PROJECT_DIR),
                        creationflags=0x08000000,
                    )
                else:
                    subprocess.Popen(
                        [sys.executable, str(PROJECT_DIR / "main.py"), "--wait-pid", str(os.getpid())],
                        cwd=str(PROJECT_DIR),
                        creationflags=0x08000000,
                    )
                self.hide()
                QTimer.singleShot(100, self.exit_snow)
                return True

            self._active_theme = package_name
            if hasattr(self, '_world'):
                self._world.set_theme(package_name)
            get_theme().load(package_name)

            self._stop_video()
            mf = self._video_config_for(package_name)
            if mf:
                self._start_video(mf)

            self._sync_transparent_ui(package_name)
            self.update()
            config_file = PROJECT_DIR / "config" / "ui.json"
            config_file.parent.mkdir(exist_ok=True)
            config_file.write_text(
                json.dumps({"active": package_name}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            self._bridge.ai_work.emit(f"\U0001f3a8 已切换到 {package_name}")
        return ok

    def _apply_wallpaper(self, package_name):
        mf_path = THEMES_DIR / package_name / "manifest.json"
        if not mf_path.exists(): return
        try:
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            wp = mf.get("wallpaper", "")
            if wp:
                wp_path = str((THEMES_DIR / package_name / wp).resolve())
                if Path(wp_path).exists():
                    ctypes.windll.user32.SystemParametersInfoW(20, 0, wp_path, 2)
        except Exception:
            pass

    def _ensure_trans_dialog(self):
        """Lazy-create TransparentDialog. Never assume native chat widgets exist."""
        if self._trans_dialog is None:
            self._trans_dialog = TransparentDialog(self._bridge, self._sw, self._sh)
        return self._trans_dialog

    def _show_native_dialog(self):
        """Show top-level chat dialog (used when Web chat is hidden)."""
        try:
            dlg = self._ensure_trans_dialog()
            dlg.show_dialog()
        except Exception as e:
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                import time
                f.write(f"{time.strftime('%H:%M:%S')} [window] show_native_dialog failed: {e}\n")

    def _hide_native_dialog(self):
        """Hide top-level chat dialog if it exists. Safe if never created."""
        dlg = getattr(self, "_trans_dialog", None)
        if dlg is not None:
            try:
                dlg.hide_dialog()
            except Exception:
                pass

    def _get_theme_mode(self, package_name: str) -> str:
        """读取主题 panel.json 的 mode 字段。返回 'default'、'chat_only' 等。"""
        panel_path = THEMES_DIR / package_name / "panel.json"
        if panel_path.exists():
            try:
                cfg = json.loads(panel_path.read_text(encoding="utf-8"))
                return cfg.get("mode", "default")
            except Exception:
                pass
        return "default"

    def _sync_transparent_ui(self, package_name):
        """视频模式：极简只留对话框。红丝带：卡片右叠+世界置顶。chat_only：纯Web聊天。普通：恢复 Web 聊天。"""
        mode = self._get_theme_mode(package_name)
        tm = get_theme()
        is_transparent = tm.get("background", "top", "#7a8f9e") == "transparent"

        # ── chat_only 模式：真·极简——整个窗口就是一个对话框 ──
        # 窗口只有对话框大小，桌面其余部分完全不被遮挡，图标/点击全部正常。
        # 不嵌 WorkerW（普通顶层窗口，键盘输入正常）。
        if mode == "chat_only":
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self._hide_native_dialog()
            # 如果之前嵌入过 WorkerW（从透明模式切换来），需要解嵌
            if self._transparent_embedded:
                try:
                    ctypes.windll.user32.SetParent(int(self.winId()), 0)
                except Exception:
                    pass
                self._transparent_embedded = False
            # 窗口缩成对话框大小，底部居中
            dlg_w = max(560, min(780, int(self._sw * 0.55)))
            dlg_h = max(360, min(480, int(self._sh * 0.50)))
            dlg_x = (self._sw - dlg_w) // 2
            dlg_y = self._sh - dlg_h - 24
            self.setGeometry(dlg_x, dlg_y, dlg_w, dlg_h)
            self._web.show()
            self._web.setGeometry(0, 0, dlg_w, dlg_h)
            # 确保 WebView 能接收键盘输入
            self._web.setFocus()
            self.activateWindow()
            if hasattr(self, '_close_btn') and self._close_btn:
                self._close_btn.hide()
            if hasattr(self, '_left_frame'):
                self._left_frame.hide()
            if hasattr(self, '_right_frame'):
                self._right_frame.hide()
            if hasattr(self, '_world') and hasattr(self._world, 'button'):
                self._world.button.hide()
            if hasattr(self, '_logo'):
                self._logo.hide()
            return

        if self._video_config:
            # 视频壁纸：隐藏卡片/Logo，用原生顶层对话框交互（不碰不存在的 _native_chat）
            web_w, web_h = adaptive_chat_size(self._sw, self._sh)
            self._web.setGeometry((self._sw - web_w)//2, self._sh - web_h - 4, web_w, web_h)
            self._web.hide()
            if hasattr(self, '_close_btn') and self._close_btn:
                self._close_btn.hide()
            if hasattr(self, '_left_frame'):
                self._left_frame.hide()
            if hasattr(self, '_right_frame'):
                self._right_frame.hide()
            if hasattr(self, '_world') and hasattr(self._world, 'button'):
                self._world.button.hide()
            if hasattr(self, '_logo'):
                self._logo.hide()
            self._show_native_dialog()
            return
        if is_transparent:
            wp_path = THEMES_DIR / package_name / "红丝带壁纸.png"
            if wp_path.exists():
                # 红丝带模式：卡片右侧叠放 + 世界按钮置顶 + Web 聊天
                self._hide_native_dialog()
                web_w, web_h = adaptive_chat_size(self._sw, self._sh)
                self._web.show()
                self._web.setGeometry((self._sw - web_w)//2, self._sh - web_h - 4, web_w, web_h)
                card_w, card_h = 240, 290
                right_x = self._sw - card_w - 24
                total_h = card_h * 2 + 8
                top_y = (self._sh - total_h) // 2
                if hasattr(self, '_left_frame'):
                    self._left_frame.setFixedSize(card_w, card_h)
                    self._left_frame.move(right_x, top_y)
                    self._left_frame.show()
                if hasattr(self, '_right_frame'):
                    self._right_frame.setFixedSize(card_w, card_h)
                    self._right_frame.move(right_x, top_y + card_h + 8)
                    self._right_frame.show()
                if hasattr(self, '_world') and hasattr(self._world, 'button'):
                    self._world.button.move((self._sw - 130) // 2, 20)
                    self._world.button.show()
                if hasattr(self, '_logo'):
                    self._logo.hide()
            else:
                # 极简透明模式：原生对话框 + 关闭按钮，窗口透底
                self.setAttribute(Qt.WA_TranslucentBackground, True)
                self.setAutoFillBackground(False)
                # WorkerW 嵌入 — 窗口变壁纸层，桌面图标浮在上面
                _ep = getattr(self, '_embed_epoch', 0)

                QTimer.singleShot(2000, lambda: self._embed_to_desktop(_ep))
                self._web.hide()
                if hasattr(self, '_close_btn') and self._close_btn:
                    self._close_btn.hide()
                if hasattr(self, '_left_frame'):
                    self._left_frame.hide()
                if hasattr(self, '_right_frame'):
                    self._right_frame.hide()
                if hasattr(self, '_world') and hasattr(self._world, 'button'):
                    self._world.button.hide()
                if hasattr(self, '_logo'):
                    self._logo.hide()
                self._show_native_dialog()
        else:
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)
            # 从 chat_only 对话框窗口切回来时恢复全屏
            geo = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(geo)
            self._hide_native_dialog()
            # 解嵌 WorkerW（如果之前嵌入了）
            if self._transparent_embedded:
                try:
                    ctypes.windll.user32.SetParent(int(self.winId()), 0)
                except Exception:
                    pass
                self._transparent_embedded = False
                self._hide_desktop_icons()
            # 恢复 WebEngine 聊天
            self._web.show()
            web_w, web_h = adaptive_chat_size(self._sw, self._sh)
            self._web.setGeometry((self._sw - web_w)//2, self._sh - web_h - 4, web_w, web_h)
            if hasattr(self, '_left_frame'):
                self._left_frame.setFixedSize(260, 380)
                self._left_frame.move(22, self._sh - 380 - 120)
                self._left_frame.show()
            if hasattr(self, '_right_frame'):
                self._right_frame.setFixedSize(260, 380)
                self._right_frame.move(self._sw - 260 - 22, self._sh - 380 - 120)
                self._right_frame.show()
            if hasattr(self, '_world') and hasattr(self._world, 'button'):
                self._world.button.move((self._sw - 130)//2, 12)
                self._world.button.show()
            if hasattr(self, '_logo'):
                self._logo.show()
            if hasattr(self, '_close_btn') and self._close_btn:
                self._close_btn.show()

    def _reposition_cards(self):
        if not hasattr(self, '_left_frame') or not hasattr(self, '_right_frame'):
            return
        tm = get_theme()
        layout = tm.get_section("_layout")
        if not layout:
            return
        card_w = layout.get("card_w", 260)
        card_h = layout.get("card_h", 380)
        def _rx(v, d): return self._sw - card_w - 22 if v == "auto_right" else (d if v is None else v)
        def _ry(v, d): return self._sh - card_h - 120 if v == "auto_bottom" else (d if v is None else v)
        lx = _rx(layout.get("left_x"), 22)
        ly = _ry(layout.get("left_y"), self._sh - card_h - 120)
        rx = _rx(layout.get("right_x"), self._sw - card_w - 22)
        ry = _ry(layout.get("right_y"), self._sh - card_h - 120)
        self._left_frame.setFixedSize(card_w, card_h)
        self._left_frame.move(lx, ly)
        self._right_frame.setFixedSize(card_w, card_h)
        self._right_frame.move(rx, ry)

    # ── Tray ──

    def _setup_tray(self):
        pm = QPixmap(32, 32)
        pm.fill(QColor("#7a8f9e"))
        pr = QPainter(pm)
        pr.setPen(QColor("#fff"))
        pr.setFont(cn_font(16))
        pr.drawText(pm.rect(), Qt.AlignCenter, "\u2745")
        pr.end()
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(QIcon(pm))
        self._tray.setToolTip("Snow")
        # 持久引用：QSystemTrayIcon.setContextMenu 不接管所有权，
        # 局部变量会被 GC 回收，右键托盘访问悬空指针 → segfault
        self._tray_menu = QMenu()
        self._tray_menu.addAction("\u9000\u51fa").triggered.connect(self.exit_snow)
        self._tray.setContextMenu(self._tray_menu)
        self._tray.show()

    # ── Events ──

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_web'):
            if getattr(self, '_minimal_mode', False):
                # 真·极简：WebView 始终铺满整个（对话框大小的）窗口
                self._web.setGeometry(0, 0, self.width(), self.height())
            else:
                web_w, web_h = adaptive_chat_size(self._sw, self._sh)
                self._web.setGeometry(
                    (self.width() - web_w) // 2,
                    self.height() - web_h - 4,
                    web_w, web_h
                )

    def _auto_greet(self):
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [window] auto_greet firing\n")
        self._bridge.ask(
            "\u4f60\u521a\u521a\u542f\u52a8\u3002\u8bf7\u5411\u7528\u6237\u6253\u62db\u547c\uff0c"
            "\u7136\u540e\u505a\u4e00\u4e2a\u7b80\u77ed\u7684\u5de5\u4f5c\u6c47\u62a5\u3002"
            "\u8bed\u6c14\u8f7b\u677e\u53cb\u597d\uff0c\u4e0d\u8d85\u8fc7\u4e09\u53e5\u8bdd\u3002"
        )

    def _open_settings_for_first_run(self):
        """首次运行：自动打开设置页面。"""
        try:
            self._bridge.open_settings()
        except Exception:
            pass

    def _push_to_bottom(self):
        hwnd = int(self.winId())
        if hwnd:
            ctypes.windll.user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x0003)

    def _safe_hide_icons(self):
        try:
            self._hide_desktop_icons()
        except Exception:
            pass

    def _hide_desktop_icons(self):
        import ctypes as _c
        from ctypes import wintypes as _w
        _u = _c.windll.user32
        hwnd = _u.FindWindowW("Progman", None)
        if hwnd:
            _u.SendMessageTimeoutW(hwnd, 0x052C, 0, 0, 0, 500, None)
        def _cb(hwnd, lp):
            n = _c.create_unicode_buffer(256)
            _u.GetClassNameW(hwnd, n, 256)
            if n.value == "WorkerW":
                sh = _u.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if sh:
                    lv = _u.FindWindowExW(sh, 0, "SysListView32", "FolderView")
                    if lv and _u.IsWindowVisible(lv):
                        _u.ShowWindow(lv, 0)
                        return False
            return True
        _WEP = _c.WINFUNCTYPE(_w.BOOL, _w.HWND, _w.LPARAM)
        _u.EnumWindows(_WEP(_cb), 0)

    def _show_desktop_icons(self):
        import ctypes as _c
        from ctypes import wintypes as _w
        _u = _c.windll.user32
        def _cb(hwnd, lp):
            n = _c.create_unicode_buffer(256)
            _u.GetClassNameW(hwnd, n, 256)
            if n.value == "WorkerW":
                sh = _u.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if sh:
                    lv = _u.FindWindowExW(sh, 0, "SysListView32", "FolderView")
                    if lv and not _u.IsWindowVisible(lv):
                        _u.ShowWindow(lv, 5)
                        return False
            return True
        _WEP = _c.WINFUNCTYPE(_w.BOOL, _w.HWND, _w.LPARAM)
        _u.EnumWindows(_WEP(_cb), 0)

    def exit_snow(self):
        self._hide_native_dialog()
        # 停掉周期定时器，避免退出过程中回调触发网络请求
        for tname in ("_card_timer",):
            t = getattr(self, tname, None)
            if t is not None:
                try:
                    t.stop()
                except Exception:
                    pass
        try:
            self._bridge._tts._stop_playback()
        except Exception:
            pass
        self._stop_video()
        self._show_desktop_icons()
        if hasattr(self, '_tray'):
            self._tray.hide()
        self.hide()
        QApplication.instance().quit()
