"""Todo service — CRUD with JSON persistence, thread-safe + atomic write."""
import json, os, threading
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
TODOS_FILE = PROJECT_DIR / "data" / "todos.json"
_lock = threading.Lock()


def _load() -> list:
    if not TODOS_FILE.exists():
        return []
    try:
        raw = json.loads(TODOS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []  # 文件损坏：从空列表重新开始，不让待办功能整体瘫痪
    # 兼容旧格式：list of strings
    if isinstance(raw, list) and raw and isinstance(raw[0], str):
        return [{"text": t, "done": False} for t in raw]
    if isinstance(raw, list):
        return raw
    return []  # dict 等非法结构


def _save(todos: list):
    """原子写：tmp + os.replace，写一半崩溃不损坏原文件。"""
    (PROJECT_DIR / "data").mkdir(exist_ok=True)
    tmp = TODOS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(todos, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, TODOS_FILE)


def get_all() -> list:
    with _lock:
        return _load()


def add(text: str):
    with _lock:
        todos = _load()
        if not any(t["text"] == text for t in todos):
            todos.append({"text": text, "done": False})
        _save(todos)


def toggle(idx: int):
    with _lock:
        todos = _load()
        if 0 <= idx < len(todos):
            todos[idx]["done"] = not todos[idx].get("done", False)
        _save(todos)


def remove(idx: int):
    with _lock:
        todos = _load()
        if 0 <= idx < len(todos):
            todos.pop(idx)
        _save(todos)


def get_as_strings() -> list:
    with _lock:
        todos = _load()
        return [t.get("text", "") for t in todos]
