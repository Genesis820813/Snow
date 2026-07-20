"""Tool: desktop organization — organize_desktop."""
from pathlib import Path

from snow.paths import PROJECT_DIR

TOOLS = [
    ("organize_desktop", "\u6574\u7406\u684c\u9762\uff1a\u5c06\u6563\u4e71\u6587\u4ef6\u6536\u96c6\u5230\u65e5\u671f\u547d\u540d\u7684\u6587\u4ef6\u5939\u4e2d", {}, []),
]


def _organize_desktop(args):
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "\u627e\u4e0d\u5230\u684c\u9762\u76ee\u5f55"

    dest = desktop / "\u684c\u9762\u6587\u4ef6"
    dest.mkdir(exist_ok=True)

    moved = 0
    for item in desktop.iterdir():
        if item.is_dir():
            continue
        if item.name.startswith((".", "~")):
            continue
        if item.suffix.lower() == ".lnk":
            continue
        df = dest / item.name
        if df.exists():
            df = dest / (item.stem + "_" + str(moved) + item.suffix)
        item.rename(df)
        moved += 1

    if moved == 0:
        return "\u684c\u9762\u5f88\u6574\u9f50\uff0c\u6ca1\u6709\u6563\u4e71\u6587\u4ef6~"
    return f"\u5df2\u5c06 {moved} \u4e2a\u6563\u6587\u4ef6\u5f52\u5165\u300c\u684c\u9762\u6587\u4ef6\u300d\u6587\u4ef6\u5939\u3002\u70b9\u51fb\u9876\u90e8\u300c\u4e16\u754c\u300d\u6309\u94ae\u5237\u65b0\u89c6\u56fe\u5373\u53ef\u770b\u5230\u66f4\u65b0\u3002"


HANDLERS = {
    "organize_desktop": _organize_desktop,
}
