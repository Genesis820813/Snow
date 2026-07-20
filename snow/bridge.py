"""Snow Bridge — QWebChannel bridge: Python ↔ JavaScript UI."""
import json, threading, subprocess, os
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QApplication

from snow.paths import PROJECT_DIR

_bridge_instance = None


class SnowBridge(QObject):
    """Bridge object exposed to JavaScript via QWebChannel."""

    ai_token = Signal(str)
    ai_done = Signal(str)
    ai_error = Signal(str)
    ai_sentence = Signal(str)
    tts_ready = Signal(str)
    apps_loaded = Signal(str)
    state_changed = Signal(str)
    exit_requested = Signal()
    ai_work = Signal(str)
    ai_tool_status = Signal(str)  # 推送到 web 前端显示工具状态
    todos_changed = Signal()
    world_closed = Signal()
    world_toggle = Signal()
    world_show = Signal(object)
    file_picked = Signal(str)

    def __init__(self):
        global _bridge_instance
        _bridge_instance = self
        super().__init__()
        self._ai = None
        self._parent_window = None

        from snow.services.tts import TTSEngine
        self._tts = TTSEngine()

        from snow.services.monitor import SystemMonitor
        self._monitor = SystemMonitor()

    # ── AI ──

    @Slot(str)
    def ask(self, text: str):
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [bridge] ask({text[:50]}...)\n")

        self._tts._stop_playback()

        if self._ai is None:
            with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
                f.write(f"  creating new SnowAI\n")
            from snow.agent import SnowAI
            self._ai = SnowAI()
            self._ai._bridge = self
            self._ai.token_signal.connect(lambda t: self.ai_token.emit(t))
            self._ai.done_signal.connect(lambda full: self._on_ai_complete(full))
            self._ai.error_signal.connect(lambda e: self.ai_error.emit(e))
            self._ai.sentence_signal.connect(lambda s: self.ai_sentence.emit(s))
            self._ai.tool_signal.connect(lambda label: self._on_tool(label))

        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            f.write(f"  calling ai.ask, provider={getattr(self._ai, '_provider', '?')}\n")
        self._ai.ask(text)

    def _on_tool(self, label: str):
        from snow.services.worklog import record
        record(label, "running")
        self.ai_work.emit(label)
        self.ai_tool_status.emit(label)  # 推送给 web 前端显示

    def _on_ai_complete(self, full: str):
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [bridge] ai_complete, about to emit ai_done\n")
        from snow.services.worklog import mark_last_done
        mark_last_done()
        self.ai_done.emit(full)
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [bridge] ai_done emitted OK\n")

    # ── Model ──

    @Slot(result=str)
    def get_model_config(self) -> str:
        from snow.agent import load_model_config
        return json.dumps(load_model_config(), ensure_ascii=False)

    @Slot(str, str)
    def switch_model(self, provider: str, model_id: str):
        cfg_file = PROJECT_DIR / "config" / "model_config.json"
        cfg = {}
        if cfg_file.exists():
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        cfg["provider"] = provider
        cfg["model"] = model_id
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        self._ai = None
        self.state_changed.emit(json.dumps({"model": model_id, "provider": provider}))

    # ── TTS ──

    @Slot(str)
    def speak(self, text: str):
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} [bridge] speak() called, text={text[:60]}...\n")
        try:
            self._tts.speak(text)
        except Exception:
            import traceback
            with open(str(PROJECT_DIR / "crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n--- TTS speak crash ---\n{traceback.format_exc()}\n")

    @Slot(result=bool)
    def toggle_tts(self):
        result = self._tts.toggle()
        self.state_changed.emit(json.dumps({"tts": result}))
        return result

    @Slot(result=str)
    def get_voice(self) -> str:
        vf = PROJECT_DIR / "data" / "voice.txt"
        if vf.exists():
            v = vf.read_text(encoding="utf-8").strip()
            if v:
                return v.split("\n")[0].strip()
        return "Xiaoxiao"

    @Slot(str)
    def set_voice(self, voice: str):
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        (PROJECT_DIR / "data" / "voice.txt").write_text(voice, encoding="utf-8")

    @Slot(result=str)
    def get_voices(self) -> str:
        voices = self._tts.get_voices()
        return json.dumps(voices)

    # ── Apps / World ──

    @Slot(result=str)
    def get_apps(self) -> str:
        try:
            import sys
            sys.path.insert(0, str(PROJECT_DIR))
            from snow.scanner import scan_desktop_shortcuts, get_special_desktop_items
            from pathlib import Path as P

            apps = []
            files = []

            for s in get_special_desktop_items():
                apps.append({"name": s["name"], "target": s.get("target", "")})

            for a in scan_desktop_shortcuts(classify=False):
                apps.append({"name": a["name"], "target": a.get("target", "")})

            desk = P.home() / "Desktop"
            if desk.exists():
                for item in sorted(desk.iterdir()):
                    if item.name.startswith("."):
                        continue
                    if item.suffix.lower() == ".lnk":
                        continue
                    display = item.name + (" \U0001f4c1" if item.is_dir() else "")
                    files.append({"name": display, "target": str(item)})

            seen = set()
            unique_apps = []
            for a in apps:
                n = a.get("name", "").lower()
                if n not in seen:
                    seen.add(n)
                    unique_apps.append(a)

            return json.dumps({"apps": unique_apps, "files": files}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"apps": [], "files": []})

    @Slot(str)
    def launch_app(self, name: str):
        try:
            import sys, os as _os
            sys.path.insert(0, str(PROJECT_DIR))
            from snow.scanner import scan_desktop_shortcuts, get_special_desktop_items
            from pathlib import Path as P

            nl = name.lower()

            for s in get_special_desktop_items():
                if s["name"] == name:
                    subprocess.Popen(["explorer", s["path"]], shell=True, creationflags=0x08000000)
                    return

            desk = P.home() / "Desktop"
            for item in desk.iterdir():
                if item.name.startswith("."): continue
                if item.suffix.lower() == ".lnk": continue
                display = item.name + (" \U0001f4c1" if item.is_dir() else "")
                if display == name:
                    os.startfile(str(item))
                    return

            apps = scan_desktop_shortcuts(classify=False)
            for app in apps:
                if nl in app.get("name", "").lower():
                    target = app.get("target", "")
                    if target and P(target).exists():
                        os.startfile(target)
                        return
                    path = app.get("path", "")
                    if path and P(path).exists():
                        os.startfile(path)
                        return

            if name in ("\u6b64\u7535\u8111", "\u56de\u6536\u7ad9"):
                shell = "shell:MyComputer" if name == "\u6b64\u7535\u8111" else "shell:RecycleBinFolder"
                subprocess.Popen(["explorer", shell], shell=True, creationflags=0x08000000)
        except Exception as e:
            print(f"[Bridge] launch_app error: {e}")

    # ── Settings ──

    @Slot()
    def open_settings(self):
        try:
            import sys
            sys.path.insert(0, str(PROJECT_DIR))
            from snow.settings import SettingsCenter
            self._settings = SettingsCenter()
            self._settings.model_changed.connect(self._on_model_switched)
            self._settings.show()
        except Exception as e:
            print(f"[Bridge] Settings failed: {e}")

    def _on_model_switched(self):
        self._ai = None
        self.ai_work.emit("\U0001f504 \u6a21\u578b\u5df2\u5207\u6362")

    # ── File ──

    @Slot()
    def pick_file(self):
        """打开文件选择对话框，读取文本文件内容，通过 file_picked 信号发送。"""
        from PySide6.QtWidgets import QFileDialog
        import os as _os

        paths, _ = QFileDialog.getOpenFileNames(
            None, "\u9009\u62e9\u6587\u4ef6", "",
            "\u6240\u6709\u6587\u4ef6 (*.*);;\u56fe\u7247 (*.png *.jpg *.jpeg *.gif *.bmp);;\u6587\u6863 (*.pdf *.docx *.txt *.md)"
        )
        if not paths:
            return

        # 文本文件的扩展名（可安全读取为字符串显示）
        TEXT_EXTS = {
            ".txt", ".md", ".py", ".js", ".ts", ".html", ".htm", ".css",
            ".json", ".yaml", ".yml", ".xml", ".csv", ".log", ".cfg",
            ".ini", ".toml", ".sh", ".bat", ".ps1", ".c", ".cpp", ".h",
            ".hpp", ".java", ".kt", ".rs", ".go", ".rb", ".php", ".sql",
            ".r", ".m", ".swift", ".vue", ".svelte", ".jsx", ".tsx",
            ".env", ".gitignore", ".dockerignore", ".editorconfig",
            ".nix", ".lua", ".tex", ".Makefile", ".cmake",
        }

        parts = []
        for path in paths:
            fname = _os.path.basename(path)
            ext = _os.path.splitext(fname)[1].lower()
            # 无扩展名的文件也可能可读（如 Makefile, LICENSE），检查大小
            size_mb = _os.path.getsize(path) / (1024 * 1024)
            if ext in TEXT_EXTS or ext == "":
                if size_mb > 5:
                    # 太大，只传路径
                    parts.append(f"FILE:{path}")
                else:
                    try:
                        content = Path(path).read_text(encoding="utf-8")
                        parts.append(f"TEXT:{fname}\n{content}")
                    except UnicodeDecodeError:
                        try:
                            content = Path(path).read_text(encoding="gbk")
                            parts.append(f"TEXT:{fname}\n{content}")
                        except Exception:
                            parts.append(f"FILE:{path}")
                    except Exception:
                        parts.append(f"FILE:{path}")
            else:
                parts.append(f"FILE:{path}")

        if parts:
            self.file_picked.emit("\n---FILE_SEPARATOR---\n".join(parts))

    @Slot(str, str, result=str)
    def save_uploaded_file(self, name: str, b64data: str):
        import base64
        upload_dir = PROJECT_DIR / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        try:
            raw = base64.b64decode(b64data)
            path = upload_dir / name
            path.write_bytes(raw)
            return str(path)
        except Exception as e:
            return f"\u4fdd\u5b58\u5931\u8d25: {e}"

    # ── World ──

    @Slot()
    def close_world(self):
        self.world_closed.emit()

    @Slot()
    def toggle_world(self):
        self.world_toggle.emit()

    @Slot(str)
    def show_world_icons(self, json_data: str):
        try:
            data = json.loads(json_data)
        except Exception:
            data = {"apps": [], "files": []}
        self.world_show.emit(data)

    @Slot()
    def exit_snow(self):
        self.exit_requested.emit()

    # ── UI Management ──

    @Slot(result=str)
    def get_ui_list(self) -> str:
        """返回所有可用 UI package 列表。"""
        loader = getattr(self, "_ui_loader", None)
        if loader:
            packages = loader.list_ui()
            return json.dumps(packages, ensure_ascii=False)
        return json.dumps([])

    @Slot(str, result=bool)
    def switch_ui(self, package_name: str) -> bool:
        """切换 UI 主题。返回是否成功。"""
        win = self._parent_window
        if win and hasattr(win, "switch_ui"):
            return win.switch_ui(package_name)
        return False

    # ── Info Cards ──

    @Slot(result=str)
    def get_weather(self) -> str:
        from snow.services.weather import get_weather
        try:
            data = get_weather()
            return json.dumps(data)
        except Exception as e:
            return json.dumps({"icon": "\u2600", "temp": "--", "city": "\u7f51\u7edc\u5f02\u5e38"})

    @Slot(result=str)
    def get_hotsearch(self) -> str:
        from snow.services.hotsearch import get_hotsearch
        try:
            items = get_hotsearch()
            return json.dumps(items)
        except Exception:
            return json.dumps([])

    @Slot(result=str)
    def get_work_log(self) -> str:
        from snow.services.worklog import get_recent
        logs = get_recent(8)
        return json.dumps(logs)

    @Slot(str, str)
    def record_work(self, action: str, status: str = "done"):
        from snow.services.worklog import record
        record(action, status)

    @Slot(result=str)
    def get_system_stats(self) -> str:
        return json.dumps(self._monitor.get())

    @Slot(result=str)
    def get_todos(self) -> str:
        from snow.services.todos import get_all
        return json.dumps(get_all())

    @Slot(str)
    def add_todo(self, text: str):
        from snow.services.todos import add
        add(text)
        self.todos_changed.emit()

    @Slot(int)
    def toggle_todo(self, idx: int):
        from snow.services.todos import toggle
        toggle(idx)
        self.todos_changed.emit()

    @Slot(int)
    def remove_todo(self, idx: int):
        from snow.services.todos import remove
        remove(idx)
        self.todos_changed.emit()
