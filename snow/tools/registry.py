"""Tool registry — auto-collect TOOLS from all tool modules, route execution."""
import importlib
import json
from pathlib import Path

_TOOL_MODULES = [
    "snow.tools.app",
    "snow.tools.file",
    "snow.tools.web",
    "snow.tools.system",
    "snow.tools.desktop",
    "snow.tools.document",
    "snow.tools.world",
    "snow.tools.snow",
    "snow.tools.classify",
]

_tool_defs = []
_handlers = {}
_loaded = False


def _load_all():
    global _loaded, _tool_defs, _handlers
    if _loaded:
        return
    for mod_name in _TOOL_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "TOOLS"):
                _tool_defs.extend(mod.TOOLS)
            if hasattr(mod, "HANDLERS"):
                _handlers.update(mod.HANDLERS)
        except Exception as e:
            print(f"[Registry] Failed to load {mod_name}: {e}")
    _loaded = True


def get_tool_defs() -> list:
    """Return OpenAI function-calling format tool definitions."""
    _load_all()
    tools = []
    for name, desc, props, required in _tool_defs:
        params = {"type": "object", "properties": {}, "required": required}
        for pname, (ptype, pdesc) in props.items():
            params["properties"][pname] = {"type": "string", "description": pdesc}
        tools.append({"type": "function", "function": {"name": name, "description": desc, "parameters": params}})
    return tools


def execute(name: str, args: dict) -> str:
    """Execute a tool by name with given args. Returns result string."""
    _load_all()
    handler = _handlers.get(name)
    if handler is None:
        return f"\u672a\u77e5\u5de5\u5177: {name}"
    try:
        return handler(args)
    except Exception as e:
        return f"\u5de5\u5177\u51fa\u9519: {e}"


def get_label(name: str, args: dict) -> str:
    """Return a human-readable label for the tool."""
    labels = {
        "list_desktop_items": f"\U0001f4cb \u626b\u63cf\u684c\u9762\u5feb\u6377\u65b9\u5f0f",
        "resolve_shortcut": f"\U0001f50d \u89e3\u6790\u300c{args.get('name', '?')}\u300d",
        "list_desktop_files": "\U0001f4c1 \u626b\u63cf\u684c\u9762\u6587\u4ef6",
        "show_world_icons": "\U0001f30d \u6e32\u67d3\u4e16\u754c\u9762\u677f",
        "get_weather": "\U0001f324 \u83b7\u53d6\u5929\u6c14",
        "get_hotsearch": "\U0001f525 \u83b7\u53d6\u70ed\u641c",
        "get_todos": "\u2705 \u8bfb\u53d6\u5f85\u529e",
        "add_todo": "\u2795 \u6dfb\u52a0\u5f85\u529e",
        "remove_todo": "\u2716 \u79fb\u9664\u5f85\u529e",
        "open_app": f"\U0001f680 \u6253\u5f00\u300c{args.get('name', '?')}\u300d",
        "open_url": "\U0001f310 \u6253\u5f00\u7f51\u9875",
        "search_web": f"\U0001f50e \u641c\u7d22\u300c{args.get('query', '?')}\u300d",
        "run_shell": "\u26a1 \u6267\u884c\u547d\u4ee4",
        "read_file": "\U0001f4d6 \u8bfb\u53d6\u6587\u4ef6",
        "write_file": "\u270f \u5199\u5165\u6587\u4ef6",
        "list_dir": "\U0001f4c2 \u67e5\u770b\u76ee\u5f55",
        "desktop_summary": "\U0001f4cb \u626b\u63cf\u684c\u9762",
        "set_category_apps": "\U0001f4e6 \u4fdd\u5b58\u5e94\u7528\u5206\u7c7b",
        "save_memory": "\U0001f9e0 \u4fdd\u5b58\u8bb0\u5fc6",
        "organize_desktop": "\U0001f9f9 \u6574\u7406\u684c\u9762",
    }
    label = labels.get(name, f"\u2699 {name}")
    if len(label) > 35:
        label = label[:32] + "..."
    return label
