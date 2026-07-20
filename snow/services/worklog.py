"""Work log service — AI action logging."""
import json
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.parent
LOG_FILE = PROJECT_DIR / "data" / "work_log.json"


def _load() -> list:
    """读日志，损坏/非列表一律返回 []，绝不向上抛异常。

    此函数在 bridge._on_ai_complete 的信号路径上，
    一旦抛异常 ai_done 永不 emit，UI 会永久停在"思考中"。
    """
    if not LOG_FILE.exists():
        return []
    try:
        data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(entries: list):
    """原子写：先写 tmp 再 os.replace，写一半崩溃不损坏原文件。"""
    (PROJECT_DIR / "data").mkdir(exist_ok=True)
    tmp = LOG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries[-20:], ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, LOG_FILE)


def record(action: str, status: str = "done"):
    entries = _load()
    entries.append({
        "time": datetime.now().strftime("%H:%M"),
        "text": action,
        "status": status,
    })
    _save(entries)


def get_recent(n: int = 8) -> list:
    return _load()[-n:]


def mark_last_done():
    entries = _load()
    for entry in reversed(entries):
        if entry.get("status") == "running":
            entry["status"] = "done"
            _save(entries)
            return
