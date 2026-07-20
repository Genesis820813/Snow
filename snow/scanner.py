"""Snow Scanner — pure perception layer (collecting what's on desktop).

Design: "我只看到，不判断" — collects data, doesn't filter.
"""
import os
import json
import subprocess
from pathlib import Path
import pythoncom
from win32com.client import Dispatch


def resolve_shortcut(path):
    """Resolve a .lnk shortcut to its target path."""
    try:
        pythoncom.CoInitialize()
        t = Dispatch("WScript.Shell").CreateShortCut(str(path)).TargetPath
        pythoncom.CoUninitialize()
        return t or ""
    except Exception:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        return ""


def get_special_desktop_items():
    """Detect special Windows desktop icons (this PC, recycle bin, etc.) via registry.
    
    Returns list of app dicts with name, path, target, category.
    These are not .lnk files but special shell folders.
    """
    items = []
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        except FileNotFoundError:
            return items

        clsid_map = {
            "{20D04FE0-3AEA-1069-A2D8-08002B30309D}": {"name": "\u6b64\u7535\u8111", "command": "explorer.exe /e,::{20D04FE0-3AEA-1069-A2D8-08002B30309D}", "category": "\u7cfb\u7edf"},
            "{645FF040-5081-101B-9F08-00AA002F954E}": {"name": "\u56de\u6536\u7ad9", "command": "explorer.exe shell:RecycleBinFolder", "category": "\u7cfb\u7edf"},
            "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}": {"name": "\u63a7\u5236\u9762\u677f", "command": "control.exe", "category": "\u7cfb\u7edf"},
            "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}": {"name": "\u7f51\u7edc", "command": "explorer.exe shell:NetworkPlacesFolder", "category": "\u7cfb\u7edf"},
        }

        always_vis = {"{645FF040-5081-101B-9F08-00AA002F954E}"}
        for clsid, info in clsid_map.items():
            try:
                val, _ = winreg.QueryValueEx(key, clsid)
                if val == 0 or clsid in always_vis:
                    items.append({"name": info["name"], "path": "shell:" + clsid, "target": info["command"], "category": info["category"]})
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        items.append({"name": "\u56de\u6536\u7ad9", "path": "shell:{645FF040-5081-101B-9F08-00AA002F954E}", "target": "explorer.exe shell:RecycleBinFolder", "category": "\u7cfb\u7edf"})
    except Exception:
        pass
    return items


def scan_desktop_shortcuts(classify=True):
    if classify:
        from snow.classify import classify_app
    else:
        classify_app = None
    import os
    results = []
    for d in [Path.home() / "Desktop", Path("C:/Users/Public/Desktop")]:
        if not d.exists(): continue
        for root, _, files in os.walk(str(d)):
            for f in files:
                if not f.lower().endswith(".lnk"): continue
                fp = Path(root) / f
                name = fp.stem.strip()
                target = resolve_shortcut(fp)
                if not target or not Path(target).exists(): continue
                if classify:
                    results.append({"name": name, "path": str(fp), "target": target, "category": classify_app(name, target)})
                else:
                    results.append({"name": name, "path": str(fp), "target": target})
    seen = set()
    unique = []
    for a in results:
        k = a["name"].lower()
        if k not in seen:
            seen.add(k)
            unique.append(a)
    return unique





def get_taskbar_windows():
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        results = []
        seen_names = set()
        def enum_callback(hwnd, lParam):
            if not user32.IsWindowVisible(hwnd): return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0: return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if not title: return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            h = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
            if not h: return True
            try:
                eb = ctypes.create_unicode_buffer(260)
                s = wintypes.DWORD(260)
                if kernel32.QueryFullProcessImageNameW(h, 0, eb, ctypes.byref(s)):
                    en = Path(eb.value).stem
                else:
                    en = f"process_{pid.value}"
            finally:
                kernel32.CloseHandle(h)
            skip = {"explorer","dwm","shellexperiencehost","startmenuexperiencehost","systemsettings","textinputhost","applicationframehost","runtimebroker","searchui","widgets","conhost","sihost","taskhostw","ctfmon","securityhealthsystray"}
            if en.lower() in skip: return True
            if en.lower() not in seen_names:
                seen_names.add(en.lower())
                results.append({"name":title,"path":f"process:{pid.value}","target":eb.value,"category":"\u6b64\u523b"})
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        return results[:20]
    except Exception:
        return []


def scan_all_apps():
    return scan_desktop_shortcuts()
