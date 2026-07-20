#!/usr/bin/env python3
"""Snow v3 — modular desktop AI assistant."""
import sys, os, subprocess

_ROOT = os.path.dirname(os.path.abspath(__file__))

# ── --wait-pid <old_pid>: 主题结构性切换重启时，新进程等待旧进程完全退出 ──
# 这比固定 sleep(3) 可靠：轮询进程句柄，最长等 15s。
if "--wait-pid" in sys.argv:
    idx = sys.argv.index("--wait-pid")
    if idx + 1 < len(sys.argv):
        try:
            old_pid = int(sys.argv[idx + 1])
            import ctypes as _ct
            SYNCHRONIZE = 0x100000
            h = _ct.windll.kernel32.OpenProcess(SYNCHRONIZE, False, old_pid)
            if h:
                _ct.windll.kernel32.WaitForSingleObject(h, 15000)  # max 15s
                _ct.windll.kernel32.CloseHandle(h)
        except Exception:
            pass
    # 从 argv 中摘掉这两个参数，避免干扰后续解析
    sys.argv.pop(idx)       # remove "--wait-pid"
    if idx < len(sys.argv):  # remove the PID value
        sys.argv.pop(idx)

# If launched with python.exe and we have a console, silently respawn with pythonw
if "pythonw" not in sys.executable.lower():
    try:
        import ctypes
        if ctypes.windll.kernel32.GetConsoleWindow():
            pw = sys.executable.replace("python.exe", "pythonw.exe")
            if os.path.exists(pw):
                subprocess.Popen([pw, __file__] + sys.argv[1:], creationflags=0x08000000)
                sys.exit(0)
    except Exception:
        pass

# Nuke stdout/stderr before any library can write to them
# encoding 必须显式 utf-8：Windows 默认 GBK，中文/emoji traceback 会二次崩溃
sys.stdout = open(os.path.join(_ROOT, "stdout.log"), 'w', encoding="utf-8", errors="replace", buffering=1)
sys.stderr = open(os.path.join(_ROOT, "stderr.log"), 'w', encoding="utf-8", errors="replace", buffering=1)

# Native-level crash tracing (SIGSEGV etc.) — dumps C-level traceback to stderr.log
import faulthandler
faulthandler.enable(file=sys.stderr, all_threads=True)

import traceback, ctypes

# Log who calls AllocConsole
_real_AllocConsole = ctypes.windll.kernel32.AllocConsole
def _hooked_AllocConsole():
    import traceback as _tb
    stack = ''.join(_tb.format_stack()[-5:-1])
    with open(os.path.join(_ROOT, "console.log"), "a", encoding="utf-8", errors="replace") as f:
        f.write(f"AllocConsole called from:\n{stack}\n---\n")
    return _real_AllocConsole()
ctypes.windll.kernel32.AllocConsole = _hooked_AllocConsole

def _excepthook(exc_type, exc_value, exc_tb):
    tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    with open(os.path.join(_ROOT, "crash.log"), "a", encoding="utf-8") as f:
        import time
        f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{tb}\n")
    sys.__excepthook__(exc_type, exc_value, exc_tb)
sys.excepthook = _excepthook

# Thread-level exception hook
import threading
_orig_thread_excepthook = threading.excepthook
def _thread_excepthook(args):
    tb = ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    with open(os.path.join(_ROOT, "crash.log"), "a", encoding="utf-8") as f:
        import time
        f.write(f"\n=== THREAD {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{tb}\n")
    _orig_thread_excepthook(args)
threading.excepthook = _thread_excepthook

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --ignore-gpu-blocklist --disable-logging --log-level=3 --allow-file-access-from-files"
os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.warning=false;qt.webengine*=false"
os.environ["QTWEBENGINE_LOG_LEVEL"] = "0"

# Silence Qt's own message handler
import logging
logging.getLogger().setLevel(logging.CRITICAL)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)
DIAG_MODE = False

from PySide6.QtWidgets import QApplication
from snow.window import SnowWindow

# ── PyInstaller 打包模式：首次启动从 _MEIPASS 迁移默认配置 ──
import snow.paths as _sp
_NEEDS_FIRST_SETUP = False
if getattr(sys, 'frozen', False):
    from snow.paths import _init_appdata, PROJECT_DIR as _APPDATA_DIR
    _init_appdata()
    # 检查是否首次运行（没有 key.txt）
    from pathlib import Path as _P
    _key_file = _P(_APPDATA_DIR) / "config" / "key.txt"
    if not _key_file.exists():
        _NEEDS_FIRST_SETUP = True

def _log_quit():
    try:
        with open(os.path.join(_ROOT, "diag.log"), "a", encoding="utf-8") as f:
            import time as _t
            f.write(f"{_t.strftime('%H:%M:%S')} [main] aboutToQuit signal received\n")
    except Exception:
        pass

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(_log_quit)
    w = SnowWindow(diag=DIAG_MODE, first_setup=_NEEDS_FIRST_SETUP)
    w.show()
    ret = app.exec()
    with open(os.path.join(_ROOT, "diag.log"), "a", encoding="utf-8", errors="replace") as f:
        f.write(f"{__import__('time').strftime('%H:%M:%S')} [main] app.exec() returned {ret}, exiting\n")
    sys.exit(ret)

if __name__ == "__main__":
    main()
