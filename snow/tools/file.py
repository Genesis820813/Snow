"""Tool: file operations — read_file, write_file, list_dir."""
from pathlib import Path

TOOLS = [
    ("read_file", "\u8bfb\u53d6\u6587\u4ef6", {"path": ("string", "\u6587\u4ef6\u8def\u5f84")}, ["path"]),
    ("write_file", "\u5199\u5165\u6587\u4ef6", {"path": ("string", "\u8def\u5f84"), "content": ("string", "\u5185\u5bb9")}, ["path", "content"]),
    ("list_dir", "\u5217\u51fa\u76ee\u5f55", {"path": ("string", "\u76ee\u5f55\u8def\u5f84")}, []),
]


def _read_file(args):
    import os
    p = Path(args.get("path", ""))
    if not p.exists():
        return "\u6587\u4ef6\u4e0d\u5b58\u5728"
    try:
        size_mb = os.path.getsize(p) / (1024 * 1024)
        if size_mb > 10:
            return f"\u6587\u4ef6\u8fc7\u5927 ({size_mb:.1f}MB)\uff0c\u62d2\u7edd\u8bfb\u53d6"
        return p.read_text("utf-8")[:4000]
    except UnicodeDecodeError:
        try:
            return p.read_text("gbk")[:4000]
        except Exception:
            return "\u65e0\u6cd5\u8bfb\u53d6"
    except Exception:
        return "\u65e0\u6cd5\u8bfb\u53d6"


def _write_file(args):
    import subprocess
    p = Path(args.get("path", ""))
    content = args.get("content", "")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, "utf-8")
    # HTML 文件（PPT 等）：写完后自动用浏览器打开预览
    auto_opened = ""
    if p.suffix.lower() == ".html":
        try:
            subprocess.Popen(["cmd", "/c", "start", str(p.resolve())],
                             creationflags=0x08000000)
            auto_opened = "，已在浏览器中打开预览"
        except Exception:
            pass
    return f"\u5df2\u5199\u5165 {len(content)} \u5b57\u7b26\u5230 {args.get('path', '')}{auto_opened}"


def _list_dir(args):
    path = args.get("path", "")
    p = Path(path) if path else Path.home()
    if not p.exists():
        return "\u76ee\u5f55\u4e0d\u5b58\u5728"
    try:
        items = []
        for it in sorted(p.iterdir()):
            items.append(("[DIR] " if it.is_dir() else "[FILE] ") + it.name)
        return "\n".join(items[:60])
    except Exception:
        return "\u65e0\u6cd5\u8bbf\u95ee"


HANDLERS = {
    "read_file": _read_file,
    "write_file": _write_file,
    "list_dir": _list_dir,
}
