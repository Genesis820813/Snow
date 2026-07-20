"""Left card — weather, time, date, city, hotsearch."""
from PySide6.QtWidgets import QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from datetime import datetime
from urllib.parse import quote
import subprocess


def cn_font(size=12, bold=False):
    for n in ["Microsoft YaHei", "SimHei", "Segoe UI"]:
        f = QFont(n, size)
        f.setBold(bold)
        if f.family() == n:
            return f
    return QFont("Segoe UI", size)


class LeftCard:
    """Left info card: weather icon/temp/date/city/time + hotsearch top 5."""

    def __init__(self, parent, card_w: int = 260, card_h: int = 380):
        self._parent = parent
        c = parent
        y = 22

        # Title
        title = self._section_title("\u5929\u6c14 \u00b7 \u65f6\u95f4", c)
        title.move(20, y)

        y = 48
        # Weather icon
        self._w_icon = QLabel("\u2600", c)
        self._w_icon.setFont(QFont("Segoe UI Emoji", 24))
        self._w_icon.setFixedSize(40, 40)
        self._w_icon.setAlignment(Qt.AlignCenter)
        self._w_icon.setStyleSheet("background:transparent;")
        self._w_icon.move(14, y)

        # Temperature
        self._w_temp = QLabel("--", c)
        self._w_temp.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self._w_temp.setStyleSheet("background:transparent;color:rgba(255,255,255,0.92);")
        self._w_temp.move(56, y + 6)

        # Date
        self._w_date = QLabel("", c)
        self._w_date.setFont(cn_font(11))
        self._w_date.setStyleSheet("background:transparent;color:rgba(255,255,255,0.68);")
        self._w_date.move(120, y + 12)

        # City
        self._w_city = QLabel("\u5b9a\u4f4d\u4e2d...", c)
        self._w_city.setFont(cn_font(11))
        self._w_city.setFixedWidth(220)
        self._w_city.setStyleSheet("background:transparent;color:rgba(255,255,255,0.30);")
        self._w_city.move(20, y + 46)

        # Time
        self._time_lbl = QLabel("--:--", c)
        self._time_lbl.setFont(cn_font(18))
        self._time_lbl.setStyleSheet("background:transparent;color:rgba(255,255,255,0.60);")
        self._time_lbl.move(20, y + 76)

        # Divider
        div = QLabel(c)
        div.setFixedSize(220, 1)
        div.move(20, y + 108)
        div.setStyleSheet("background:rgba(255,255,255,0.08);")

        # Hotsearch
        htitle = self._section_title("\u70ed\u641c", c)
        htitle.move(20, y + 120)

        self._hot_labels = []
        hot_y = y + 146
        for i in range(5):
            idx = QLabel(f"{i+1}.", c)
            idx.setFont(cn_font(10, True))
            idx.setFixedWidth(28)
            idx.move(16, hot_y)
            idx.setStyleSheet("background:transparent;color:rgba(255,120,100,0.55);")
            idx.show()

            txt = QLabel("\u52a0\u8f7d\u4e2d...", c)
            txt.setFont(cn_font(10))
            txt.setFixedWidth(195)
            txt.move(40, hot_y)
            txt.setStyleSheet("background:transparent;color:rgba(255,255,255,0.40);")
            txt.show()
            self._hot_labels.append((idx, txt))
            hot_y += 24

        # Refresh button
        self._refresh_btn = QPushButton("\u21bb \u6362\u4e00\u6279", c)
        self._refresh_btn.setFont(cn_font(9))
        self._refresh_btn.setFixedSize(52, 18)
        self._refresh_btn.move(180, hot_y + 4)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.clicked.connect(self.next_page)
        self._refresh_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.25);"
            "border-radius:6px;border:none;padding:0;}"
            "QPushButton:hover{background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.5);}"
        )
        self._refresh_btn.show()

        self._hotsearch_page = 0
        self._hotsearch_all = []

        # Time update timer
        self._update_time()
        t = QTimer(c)
        t.timeout.connect(self._update_time)
        t.start(10000)

    def _section_title(self, text, parent):
        lbl = QLabel(text, parent)
        lbl.setFont(cn_font(10, True))
        lbl.setStyleSheet(
            "background:transparent;color:rgba(255,255,255,0.28);"
            "letter-spacing:3px;padding:0;"
        )
        return lbl

    def set_weather(self, data: dict):
        if not data:
            return
        self._w_icon.setText(data.get("icon", "\u2600"))
        self._w_temp.setText(data.get("temp", "--"))
        self._w_city.setText(data.get("city", "\u672a\u77e5"))

    def set_hotsearch(self, data: list):
        if not data:
            return
        self._hotsearch_all = data
        self._hotsearch_page = 0
        self._show_page()

    def next_page(self):
        if not self._hotsearch_all:
            return
        per_page = 5
        total_pages = (len(self._hotsearch_all) + per_page - 1) // per_page
        self._hotsearch_page = (self._hotsearch_page + 1) % total_pages
        self._show_page()

    def _show_page(self):
        per_page = 5
        start = self._hotsearch_page * per_page
        page = self._hotsearch_all[start:start + per_page]
        for i, (idx_lbl, txt_lbl) in enumerate(self._hot_labels):
            if i < len(page):
                item = page[i]
                idx_lbl.setText(f"{start+i+1}.")
                raw_num = item.get("num", 0)
                try:
                    hotness = int(raw_num)
                except (ValueError, TypeError):
                    hotness = 0
                if hotness > 10000:
                    suffix = f"  \U0001f525{hotness//10000}w"
                elif hotness > 0:
                    suffix = f"  {hotness}"
                else:
                    suffix = ""
                txt_lbl.setText(item.get("word", "")[:18] + suffix)
                url = item.get("url", "")
                if not url:
                    url = f"https://www.baidu.com/s?wd={quote(item.get('word', ''))}"
                txt_lbl.setProperty("url", url)
                txt_lbl.setCursor(Qt.PointingHandCursor)
                txt_lbl.mousePressEvent = lambda e, u=url: self._open_link(u)
            else:
                idx_lbl.setText("")
                txt_lbl.setText("")

    def _open_link(self, url):
        if url:
            subprocess.Popen(["cmd", "/c", "start", url], shell=True, creationflags=0x08000000)

    def _update_time(self):
        now = datetime.now()
        self._time_lbl.setText(f"{now.hour:02d}:{now.minute:02d}")
        weekdays = ["\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09", "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d", "\u5468\u65e5"]
        wd = weekdays[now.weekday()]
        self._w_date.setText(f"{now.month}\u6708{now.day}\u65e5 {wd}")
