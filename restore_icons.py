"""Restore desktop icons hidden by Snow (SysListView32 FolderView)."""
import ctypes

u = ctypes.windll.user32
restored = []

def _cb(hwnd, lp):
    n = ctypes.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, n, 256)
    if n.value in ("WorkerW", "Progman"):
        sh = u.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if sh:
            lv = u.FindWindowExW(sh, 0, "SysListView32", "FolderView")
            if lv and not u.IsWindowVisible(lv):
                u.ShowWindow(lv, 5)  # SW_SHOW
                restored.append(lv)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
u.EnumWindows(WNDENUMPROC(_cb), 0)
print(f"restored {len(restored)} icon view(s)" if restored else "icons already visible")
