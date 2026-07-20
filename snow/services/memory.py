"""Memory service — persistent AI memories, atomic write."""
import json, os, time
from pathlib import Path

from snow.paths import PROJECT_DIR
MEMORY_FILE = PROJECT_DIR / "data" / "memory.json"


def load_all() -> list:
    if MEMORY_FILE.exists():
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            return data.get("memories", [])
        except Exception:
            pass
    return []


def _atomic_save(data: dict):
    """原子写：tmp + os.replace，写一半崩溃不损坏原文件。"""
    try:
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        tmp = MEMORY_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, MEMORY_FILE)
    except Exception:
        # 磁盘满/只读：至少不丢数据，下次读旧文件
        pass


def save(memories: list):
    data = {"updated": time.strftime("%Y-%m-%d %H:%M"), "memories": memories}
    _atomic_save(data)


def add(text: str) -> str:
    if not text or not text.strip():
        return "empty"
    memories = load_all()
    text = text.strip()
    if text not in memories:
        memories.append(text)
        save(memories)
        return "saved"
    return "duplicate"
