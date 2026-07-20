"""Right card — AI work log + todos."""
from PySide6.QtWidgets import QLabel, QTextEdit, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


def cn_font(size=12, bold=False):
    for n in ["Microsoft YaHei", "SimHei", "Segoe UI"]:
        f = QFont(n, size)
        f.setBold(bold)
        if f.family() == n:
            return f
    return QFont("Segoe UI", size)


class RightCard:
    """Right info card: AI work log (scrollable) + todo list (clickable)."""

    def __init__(self, parent, card_w: int = 260, card_h: int = 380, on_todo_click=None):
        self._parent = parent
        self._on_todo_click = on_todo_click
        c = parent
        y = 22

        # AI Work section
        atitle = self._section_title("AI \u5de5\u4f5c", c)
        atitle.move(20, y)
        y += 26

        self._ai_work_log = QTextEdit(c)
        self._ai_work_log.setReadOnly(True)
        self._ai_work_log.setFont(cn_font(9))
        self._ai_work_log.setGeometry(16, y, 228, 164)
        self._ai_work_log.setStyleSheet(
            "QTextEdit{background:transparent;color:rgba(100,200,160,0.80);"
            "border:none;padding:2px 4px;}"
            "QScrollBar:vertical{width:4px;background:transparent;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.08);border-radius:2px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        self._ai_work_log.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._ai_work_log.show()
        y += 172

        # Divider
        d2 = QLabel(c)
        d2.setFixedSize(220, 1)
        d2.move(20, y)
        d2.setStyleSheet("background:rgba(255,255,255,0.08);")
        y += 14

        # Todo section
        ttitle = self._section_title("\u5f85\u529e", c)
        ttitle.move(20, y)
        y += 28

        self._todo_container = QWidget(c)
        self._todo_container.setGeometry(18, y, 224, 110)
        self._todo_container.setStyleSheet("background:transparent;")
        self._todo_items = []

    def _section_title(self, text, parent):
        lbl = QLabel(text, parent)
        lbl.setFont(cn_font(10, True))
        lbl.setStyleSheet(
            "background:transparent;color:rgba(255,255,255,0.28);"
            "letter-spacing:3px;padding:0;"
        )
        return lbl

    def append_work(self, label: str):
        if label.startswith("  \u2192"):
            color = "rgba(180,180,180,0.70)"
        else:
            color = "rgba(100,200,160,0.85)"
        self._ai_work_log.append(f"<span style='color:{color}'>{label}</span>")
        scrollbar = self._ai_work_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def mark_work_done(self):
        self._ai_work_log.append(
            "<span style='color:rgba(255,255,255,0.15)'>\u2500\u2500 \u5b8c\u6210 \u2500\u2500</span>"
        )
        scrollbar = self._ai_work_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def render_todos(self, todos):
        for w in self._todo_items:
            w.setParent(None)
            w.deleteLater()
        self._todo_items.clear()

        c = self._todo_container
        y = 0
        base = max(0, len(todos) - 5)  # 显示尾部5条，点击回传全局索引
        for i, t in enumerate(todos[-5:]):
            text = t["text"] if isinstance(t, dict) else str(t)
            done = t.get("done", False) if isinstance(t, dict) else False

            item = QLabel(c)
            prefix = "\u2713" if done else "\u25cb"
            item.setText(f"{prefix}  {text[:28]}")
            item.setFont(cn_font(10))
            item.setFixedWidth(220)
            item.move(0, y)
            if done:
                item.setStyleSheet(
                    "background:transparent;color:rgba(255,255,255,0.15);"
                    "text-decoration:line-through;padding:2px 0;"
                )
            else:
                item.setStyleSheet(
                    "background:transparent;color:rgba(255,255,255,0.35);"
                    "padding:2px 0;"
                )
            item.setCursor(Qt.PointingHandCursor)
            if self._on_todo_click:
                item.mousePressEvent = lambda e, idx=base + i: self._on_todo_click(idx)
            item.show()
            self._todo_items.append(item)
            y += 22
