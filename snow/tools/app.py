"""Tool: app operations — open_app, close_app."""
import subprocess
from pathlib import Path

from snow.paths import PROJECT_DIR

TOOLS = [
    ("open_app", "\u6253\u5f00\u5e94\u7528\u7a0b\u5e8f", {"name": ("string", "\u5e94\u7528\u540d\u79f0")}, ["name"]),
    ("close_app", "\u5173\u95ed\u5e94\u7528\u7a0b\u5e8f", {"name": ("string", "\u8fdb\u7a0b\u540d")}, ["name"]),
]


def _open_app(args):
    import pythoncom
    import sys
    sys.path.insert(0, str(PROJECT_DIR))
    from snow.scanner import scan_desktop_shortcuts, resolve_shortcut
    name = args.get("name", "")
    apps = scan_desktop_shortcuts(classify=False)
    nl = name.lower()
    best = None
    for app in apps:
        if nl in app["name"].lower() or app["name"].lower() in nl:
            best = app
            break
    if best and best.get("target"):
        target = best["target"]
    elif best:
        target = resolve_shortcut(best["path"])
    else:
        target = None
    if target and Path(target).exists():
        subprocess.Popen([target], shell=True, creationflags=0x08000000)
        return f"\u5df2\u6253\u5f00 {best['name'] if best else name}"
    subprocess.Popen(name, shell=True, creationflags=0x08000000)
    return "\u5df2\u6253\u5f00 " + name


def _close_app(args):
    name = args.get("name", "")
    try:
        r = subprocess.run(["taskkill", "/f", "/im", name + ".exe"], capture_output=True, text=True, timeout=10, creationflags=0x08000000)
        return ("\u5df2\u5173\u95ed " + name) if r.returncode == 0 else ("\u672a\u627e\u5230\u8fdb\u7a0b: " + name)
    except Exception:
        return "\u5173\u95ed\u5931\u8d25: " + name


HANDLERS = {
    "open_app": _open_app,
    "close_app": _close_app,
}
