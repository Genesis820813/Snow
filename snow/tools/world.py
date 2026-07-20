"""Tool: world panel operations — resolve_shortcut, show_world_icons."""
import os, json, sys
from pathlib import Path

from snow.paths import PROJECT_DIR

TOOLS = [
    ("resolve_shortcut", "\u89e3\u6790\u4e00\u4e2a\u5feb\u6377\u65b9\u5f0f\u7684\u76ee\u6807\u8def\u5f84", {"name": ("string", "\u5feb\u6377\u65b9\u5f0f\u540d(\u4e0d\u542b.lnk)")}, ["name"]),
    ("show_world_icons", "\u5728\u4e16\u754c\u9762\u677f\u4e0a\u663e\u793a\u56fe\u6807\u3002data_json\u683c\u5f0f: {\"apps\":[{\"name\":\"\",\"target\":\"\"}],\"files\":[{\"name\":\"\",\"target\":\"\"}]}",
     {"data_json": ("string", "\u56fe\u6807\u6570\u636e\u7684JSON\u5b57\u7b26\u4e32")}, ["data_json"]),
]


def _get_desktop_dirs():
    dirs = [os.path.join(os.path.expanduser("~"), "Desktop")]
    pub = os.path.join(os.environ.get("PUBLIC", "C:/Users/Public"), "Desktop")
    if os.path.isdir(pub):
        dirs.append(pub)
    return dirs


def _walk_desktop_lnks(desk_dirs):
    results = []
    for desk in desk_dirs:
        for root, dirs, files in os.walk(desk):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.endswith('.lnk'):
                    stem = os.path.splitext(f)[0]
                    rel = os.path.relpath(root, desk)
                    if rel == '.':
                        results.append((stem, os.path.join(root, f)))
                    else:
                        results.append((f"{rel}/{stem}", os.path.join(root, f)))
    return results


def _resolve_shortcut(args):
    name = args.get("name", "")
    try:
        import pythoncom
        from win32com.client import Dispatch
        sys.path.insert(0, str(PROJECT_DIR))
        try:
            from snow.scanner import get_special_desktop_items
            for s in get_special_desktop_items():
                if s["name"] == name:
                    return s.get("target", "") or s.get("command", "") or ""
        except Exception:
            pass

        name_clean = name.replace('\\', '/')
        path = None
        for desk in _get_desktop_dirs():
            test = os.path.join(desk, name_clean + ".lnk")
            if os.path.exists(test):
                path = test
                break
        if path is None:
            found = None
            for desk in _get_desktop_dirs():
                for root, dirs, files in os.walk(desk):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for f in files:
                        if f.endswith('.lnk'):
                            stem = os.path.splitext(f)[0]
                            if name_clean.lower() in stem.lower() or stem.lower() in name_clean.lower():
                                found = os.path.join(root, f)
                                break
                    if found:
                        break
                if found:
                    break
            path = found
        if not path or not os.path.exists(path):
            return f"\u672a\u627e\u5230\u5feb\u6377\u65b9\u5f0f: {name}"
        pythoncom.CoInitialize()
        try:
            target = Dispatch("WScript.Shell").CreateShortCut(path).TargetPath
        finally:
            pythoncom.CoUninitialize()
        return target or "(\u7a7a)"
    except Exception as e:
        return f"\u89e3\u6790\u5931\u8d25: {e}"


def _show_world_icons(args):
    data_json = args.get("data_json", "")
    try:
        data = json.loads(data_json)
        rendered_apps = {a["name"]: a for a in data.get("apps", [])}
    except Exception:
        return "\u6570\u636e\u683c\u5f0f\u9519\u8bef"

    # 0. 极简主题没有世界面板——如实告知，不假装渲染成功
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        from snow.bridge import _bridge_instance
        win = getattr(_bridge_instance, "_parent_window", None) if _bridge_instance else None
        if win is not None and getattr(win, "_minimal_mode", False):
            return "\u5f53\u524d\u662f\u7eaf\u5bf9\u8bdd\u6781\u7b80\u4e3b\u9898\uff0c\u6ca1\u6709\u4e16\u754c\u9762\u677f\uff0c\u56fe\u6807\u65e0\u6cd5\u663e\u793a\u3002\u8bf7\u544a\u77e5\u7528\u6237\u9700\u5207\u6362\u5230 morandi \u4e3b\u9898\u624d\u80fd\u4f7f\u7528\u4e16\u754c\u529f\u80fd\u3002"
    except Exception:
        pass

    # 1. Render via bridge
    try:
        sys.path.insert(0, str(PROJECT_DIR))
        from snow.bridge import _bridge_instance
        if _bridge_instance:
            _bridge_instance.show_world_icons(data_json)
    except Exception as e:
        return f"\u663e\u793a\u5931\u8d25: {e}"

    # 2. Auto-verify: scan and check for missing
    dirs = _get_desktop_dirs()
    scanned_names = [name for name, path in _walk_desktop_lnks(dirs)]
    sys.path.insert(0, str(PROJECT_DIR))
    try:
        from snow.scanner import get_special_desktop_items
        for s in get_special_desktop_items():
            if s["name"] not in scanned_names:
                scanned_names.append(s["name"])
    except Exception:
        pass

    missing = [n for n in scanned_names if n not in rendered_apps]

    if missing:
        import pythoncom
        from win32com.client import Dispatch
        extra = []
        for name in missing:
            try:
                name_clean = name.replace('\\', '/')
                lnk_path = None
                for d in _get_desktop_dirs():
                    test = os.path.join(d, name_clean + ".lnk")
                    if os.path.exists(test):
                        lnk_path = test
                        break
                if lnk_path is None or not os.path.exists(lnk_path):
                    for d in _get_desktop_dirs():
                        found = False
                        for root, dirs2, files2 in os.walk(d):
                            dirs2[:] = [d2 for d2 in dirs2 if not d2.startswith('.')]
                            for f in files2:
                                if f.endswith('.lnk') and os.path.splitext(f)[0] == name_clean.split('/')[-1]:
                                    lnk_path = os.path.join(root, f)
                                    found = True
                                    break
                            if found:
                                break
                        if found:
                            break
                if lnk_path and os.path.exists(lnk_path):
                    pythoncom.CoInitialize()
                    try:
                        target = Dispatch("WScript.Shell").CreateShortCut(lnk_path).TargetPath
                    finally:
                        pythoncom.CoUninitialize()
                    extra.append({"name": name, "target": target or ""})
            except Exception:
                pass

        if extra:
            data["apps"] = list(data.get("apps", [])) + extra
            try:
                from snow.bridge import _bridge_instance
                if _bridge_instance:
                    _bridge_instance.show_world_icons(json.dumps(data, ensure_ascii=False))
            except Exception:
                pass
            names = ", ".join(e["name"] for e in extra)
            return f"\u5df2\u6e32\u67d3{len(rendered_apps)}\u4e2a\u3002\u590d\u6838\u53d1\u73b0\u9057\u6f0f{len(missing)}\u4e2a\uff08{names}\uff09\uff0c\u5df2\u81ea\u52a8\u8865\u4e0a\u3002\u6700\u7ec8\u5171{len(data['apps'])}\u4e2a\u5e94\u7528\u3002"
        else:
            return f"\u5df2\u6e32\u67d3{len(rendered_apps)}\u4e2a\u3002\u590d\u6838\u626b\u63cf\u5230{len(scanned_names)}\u4e2a\uff0c\u6709{len(missing)}\u4e2a\u672a\u89e3\u6790\u6210\u529f\u3002"
    else:
        return f"\u5df2\u6e32\u67d3{len(rendered_apps)}\u4e2a\u5e94\u7528\u3002\u590d\u6838\u901a\u8fc7\uff0c\u65e0\u9057\u6f0f\u3002"


HANDLERS = {
    "resolve_shortcut": _resolve_shortcut,
    "show_world_icons": _show_world_icons,
}
