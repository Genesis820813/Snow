"""Tool: Snow built-in capabilities — weather, hotsearch, todos, memory."""
import json
from pathlib import Path

from snow.paths import PROJECT_DIR

TOOLS = [
    ("get_weather", "\u83b7\u53d6\u5f53\u524d\u5929\u6c14\u4fe1\u606f", {}, []),
    ("get_hotsearch", "\u83b7\u53d6\u5fae\u535a\u70ed\u641c\u524d10\u6761", {}, []),
    ("get_todos", "\u67e5\u770b\u5f85\u529e\u5217\u8868", {}, []),
    ("add_todo", "\u6dfb\u52a0\u4e00\u6761\u5f85\u529e", {"text": ("string", "\u5f85\u529e\u5185\u5bb9")}, ["text"]),
    ("remove_todo", "\u79fb\u9664\u4e00\u6761\u5f85\u529e", {"text": ("string", "\u5f85\u529e\u5185\u5bb9")}, ["text"]),
    ("save_memory", "\u4fdd\u5b58\u4e00\u6761\u6301\u4e45\u8bb0\u5fc6\u3002\u5bf9\u8bdd\u4e2d\u7528\u6237\u900f\u9732\u504f\u597d\u6216\u4e60\u60ef\u65f6\u8c03\u7528",
     {"memory_text": ("string", "\u8981\u8bb0\u4f4f\u7684\u4e00\u53e5\u8bdd\uff0c\u7b80\u6d01\u660e\u4e86")}, ["memory_text"]),
    ("reload_theme", "\u5237\u65b0\u5f53\u524d\u4e3b\u9898\u7684Qt\u5c42\u914d\u8272\u3002\u6539\u5b8cpanel.json\u540e\u5fc5\u987b\u8c03\u7528", {}, []),
]


def _get_weather(args):
    try:
        cache = Path(PROJECT_DIR / "data" / "weather_cache.json")
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
            w = data["data"]
            return f"\u5f53\u524d{w['city']}\uff0c\u6c14\u6e29{w['temp']}\uff0c{w['icon']}"
    except Exception:
        pass
    return "\u5929\u6c14\u6570\u636e\u6682\u4e0d\u53ef\u7528"


def _get_hotsearch(args):
    try:
        cache = Path(PROJECT_DIR / "data" / "hotsearch_cache.json")
        if cache.exists():
            items = json.loads(cache.read_text(encoding="utf-8"))["data"]
            return "\u5fae\u535a\u70ed\u641c:\n" + "\n".join(
                f"{i+1}. {it['word']}" for i, it in enumerate(items[:10])
            )
    except Exception:
        pass
    return "\u70ed\u641c\u6682\u4e0d\u53ef\u7528"


def _get_todos(args):
    try:
        from snow.services.todos import get_all
        todos = get_all()
        if todos:
            items = []
            for t in todos:
                mark = "\u25cf" if t.get("done") else "\u25cb"
                items.append(f"{mark} {t['text']}")
            return "\u5f85\u529e:\n" + "\n".join(items)
        return "\u5f53\u524d\u6ca1\u6709\u5f85\u529e"
    except Exception:
        return "\u5f85\u529e\u8bfb\u53d6\u5931\u8d25"


def _add_todo(args):
    text = args.get("text", "").strip()
    if not text:
        return "\u5f85\u529e\u5185\u5bb9\u4e0d\u80fd\u4e3a\u7a7a"
    try:
        from snow.services.todos import get_all, add
        if any(t["text"] == text for t in get_all()):
            return "\u5df2\u7ecf\u5b58\u5728"
        add(text)
        _notify_todos_changed()
        return f"\u5df2\u6dfb\u52a0\u5f85\u529e: {text}"
    except Exception as e:
        return f"\u6dfb\u52a0\u5931\u8d25: {e}"


def _remove_todo(args):
    text = args.get("text", "")
    try:
        from snow.services.todos import get_all, remove
        todos = get_all()
        idx = next((i for i, t in enumerate(todos) if t["text"] == text), -1)
        if idx < 0:
            return f"\u672a\u627e\u5230: {text}"
        remove(idx)
        _notify_todos_changed()
        return f"\u5df2\u79fb\u9664: {text}"
    except Exception as e:
        return f"\u79fb\u9664\u5931\u8d25: {e}"


def _notify_todos_changed():
    """待办变化后通知右卡片刷新（极简模式无卡片，静默跳过）。"""
    try:
        from snow.bridge import _bridge_instance
        if _bridge_instance:
            _bridge_instance.todos_changed.emit()
    except Exception:
        pass


def _save_memory(args):
    from snow.services.memory import add
    result = add(args.get("memory_text", ""))
    if result == "saved":
        return f"\u5df2\u8bb0\u5f55\u8bb0\u5fc6: {args.get('memory_text', '')}"
    elif result == "duplicate":
        return "\u8fd9\u6761\u5df2\u7ecf\u8bb0\u8fc7\u4e86"
    return "\u672a\u63d0\u4f9b\u8bb0\u5fc6\u5185\u5bb9"


def _reload_theme(args):
    """刷新当前主题的Qt层配色"""
    from snow.theme_manager import get_manager
    from snow.ui_loader import THEMES_DIR
    from snow.bridge import _bridge_instance
    mgr = get_manager()
    mgr.load(mgr.current)
    return f"\u5df2\u5237\u65b0\u4e3b\u9898 {mgr.current} \u7684Qt\u5c42\u914d\u8272"


HANDLERS = {
    "get_weather": _get_weather,
    "get_hotsearch": _get_hotsearch,
    "get_todos": _get_todos,
    "add_todo": _add_todo,
    "remove_todo": _remove_todo,
    "save_memory": _save_memory,
    "reload_theme": _reload_theme,
}
