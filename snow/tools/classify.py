"""Tool: classification — classify_app, desktop_summary, set_category_apps."""
import json, sys
from pathlib import Path

from snow.paths import PROJECT_DIR

TOOLS = [
    ("classify_app", "\u5224\u65ad\u5e94\u7528\u5c5e\u4e8e\u54ea\u4e2a\u5206\u7c7b", {"app_name": ("string", "\u5e94\u7528\u540d")}, ["app_name"]),
    ("desktop_summary", "\u626b\u63cf\u684c\u9762\u6240\u6709\u5feb\u6377\u65b9\u5f0f\uff08\u542b\u7279\u6b8a\u9879\u76ee\uff09\uff0c\u5217\u51fa\u4f9b\u4f60\u5206\u7c7b", {}, []),
    ("set_category_apps", "\u5c06\u626b\u63cf\u5230\u7684\u5e94\u7528\u4fdd\u5b58\u5230\u684c\u9762\u3002\u6240\u6709\u5e94\u7528\u7edf\u4e00\u653e\u5728\u2018\u5e94\u7528\u2019\u5217\u8868\u91cc",
     {"classified_json": ("string", "JSON: {'\u5e94\u7528':[...]}")}, ["classified_json"]),
]


def _load_app_cache():
    f = PROJECT_DIR / "data" / "app_cache.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_app_cache(cache):
    try:
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        (PROJECT_DIR / "data" / "app_cache.json").write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _classify_app(args):
    sys.path.insert(0, str(PROJECT_DIR))
    from snow.classify import classify_app
    name = args.get("app_name", "")
    category = classify_app(name, "")
    return f"{name} \u2192 {category}"


def _desktop_summary(args):
    sys.path.insert(0, str(PROJECT_DIR))
    from snow.scanner import scan_desktop_shortcuts, get_special_desktop_items
    from snow.classify import classify_app

    cache = _load_app_cache()
    all_apps = []

    for special in get_special_desktop_items():
        key = special["name"].lower()
        if key not in cache:
            cache[key] = {
                "name": special["name"],
                "path": special["path"],
                "target": special["target"],
                "category": special["category"],
            }
        all_apps.append({
            "name": special["name"],
            "path": special["path"],
            "target": special["target"],
            "category": cache[key].get("category", special["category"]),
        })

    raw_apps = scan_desktop_shortcuts(classify=False)
    for app in raw_apps:
        key = app["name"].lower()
        if key not in cache:
            cat = classify_app(app["name"], app.get("target", ""))
            cache[key] = {
                "name": app["name"],
                "path": app.get("path", ""),
                "target": app.get("target", ""),
                "category": cat,
            }
        all_apps.append({
            "name": app["name"],
            "path": app.get("path", ""),
            "target": app.get("target", ""),
            "category": cache[key].get("category", "\u7cfb\u7edf"),
        })

    # Desktop folders
    desktop = Path.home() / "Desktop"
    try:
        for item in sorted(desktop.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith((".", "~")):
                continue
            try:
                contents = []
                for sub in sorted(item.iterdir()):
                    suffix = "/" if sub.is_dir() else ""
                    contents.append(sub.name + suffix)
                preview = ", ".join(contents[:5])
                if len(contents) > 5:
                    preview += f" ...(+{len(contents)-5})"
            except Exception:
                preview = "(\u65e0\u6cd5\u8bfb\u53d6)"
            folder_name = f"{item.name} (\u6587\u4ef6\u5939)"
            key = folder_name.lower()
            if key not in cache:
                cache[key] = {
                    "name": folder_name,
                    "path": str(item),
                    "target": preview,
                    "category": "\u7cfb\u7edf",
                }
            all_apps.append({
                "name": folder_name,
                "path": str(item),
                "target": cache[key].get("target", preview),
                "category": cache[key].get("category", "\u7cfb\u7edf"),
            })
    except Exception:
        pass

    _save_app_cache(cache)

    seen = set()
    unique_apps = []
    for a in all_apps:
        k = a["name"].lower()
        if k not in seen:
            seen.add(k)
            unique_apps.append(a)

    return json.dumps(unique_apps, ensure_ascii=False)


def _set_category_apps(args):
    try:
        curated = json.loads(args.get("classified_json", "{}"))
    except Exception as e:
        return f"JSON\u89e3\u6790\u5931\u8d25: {e}"

    # 增量合并：在现有缓存基础上更新，分批分类不互相覆盖
    new_cache = _load_app_cache()
    total_count = 0
    valid_cats = ("\u7cfb\u7edf", "\u529e\u516c", "\u793e\u4ea4", "\u5a31\u4e50", "\u521b\u4f5c", "\u6b64\u523b")
    for cat, apps in curated.items():
        if cat not in valid_cats:
            continue
        for app in apps:
            if not isinstance(app, dict):
                continue
            name = app.get("name", "")
            if not name:
                continue
            key = name.lower()
            new_cache[key] = {
                "name": name,
                "path": app.get("path", ""),
                "target": app.get("target", ""),
                "category": cat,
            }
            total_count += 1

    _save_app_cache(new_cache)
    return f"\u5df2\u5e94\u7528 {total_count} \u4e2a\u5e94\u7528\u5230\u516d\u5206\u7c7b\u680f\uff08\u7d2f\u8ba1 {len(new_cache)} \u4e2a\uff09"


HANDLERS = {
    "classify_app": _classify_app,
    "desktop_summary": _desktop_summary,
    "set_category_apps": _set_category_apps,
}
