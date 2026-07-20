"""Hotsearch service — Baidu/Weibo trending topics with fallbacks."""
import json, time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent

# Import original hotsearch module from V2
import sys
from snow.services._hotsearch_legacy import get_hotsearch as _fetch_raw


def get_hotsearch() -> list:
    cache_file = PROJECT_DIR / "data" / "hotsearch_cache.json"
    now = time.time()
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            if now - cache.get("ts", 0) < 600:
                return cache["data"]
        except Exception:
            pass  # 缓存损坏：当作过期，重新拉取

    try:
        source, raw = _fetch_raw("auto")
        items = [{"word": item["title"], "num": item.get("hot_score", 0)} for item in raw]
        if items:
            (PROJECT_DIR / "data").mkdir(exist_ok=True)
            cache_file.write_text(json.dumps(
                {"ts": now, "data": items}, ensure_ascii=False
            ), encoding="utf-8")
            return items
    except Exception as e:
        print(f"[Hotsearch] fetch failed: {e}", flush=True)

    # 失败也刷新缓存 ts，避免频繁重试网络
    try:
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        if cache_file.exists():
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        else:
            cache = {}
        cache["ts"] = now
        cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8")).get("data")
            return data if data else []
    except Exception:
        pass
    return []
