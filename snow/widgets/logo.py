"""Snow Logo — rotating snowflake with 3-layer glow."""
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QTransform

from snow.theme_manager import get_manager, on_theme_reload


def _parse_rgba(rgba_str: str):
    try:
        s = rgba_str.replace("rgba(", "").replace(")", "")
        parts = [float(x.strip()) for x in s.split(",")]
        return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3] * 255) if len(parts) > 3 else 255)
    except Exception:
        return (200, 220, 240, 110)


class LogoWidget(QWidget):
    """Rotating snowflake logo — 3-layer glow via DropShadow, sharp body."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)

        self._glow1 = QLabel(self)
        self._glow1.setFixedSize(200, 200)
        self._glow1.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._glow1_effect = QGraphicsDropShadowEffect(self._glow1)
        self._glow1.setGraphicsEffect(self._glow1_effect)

        self._glow2 = QLabel(self)
        self._glow2.setFixedSize(200, 200)
        self._glow2.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._glow2_effect = QGraphicsDropShadowEffect(self._glow2)
        self._glow2.setGraphicsEffect(self._glow2_effect)

        self._glow3 = QLabel(self)
        self._glow3.setFixedSize(200, 200)
        self._glow3.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._glow3_effect = QGraphicsDropShadowEffect(self._glow3)
        self._glow3.setGraphicsEffect(self._glow3_effect)

        self._apply_theme()
        on_theme_reload(self._apply_theme)

        self._sync_glow_labels()

    def _apply_theme(self):
        tm = get_manager()
        glyph = tm.get("logo", "glyph", "❆")
        self._glyph = glyph

        # 容器尺寸
        w = tm.get("logo", "width", 200)
        h = tm.get("logo", "height", 200)
        self.setFixedSize(w, h)
        # 居中重算
        from PySide6.QtWidgets import QApplication
        geo = QApplication.primaryScreen().availableGeometry()
        self.move((geo.width() - w) // 2, (geo.height() - h) // 2)

        # 字体大小
        self._font_size = tm.get("logo", "font_size", 130)

        # 旋转开关
        rotate = tm.get("logo", "rotate", True)
        if rotate and not self._timer.isActive():
            self._timer.start(50)
        elif not rotate and self._timer.isActive():
            self._timer.stop()

        # 可见性
        visible = tm.get("logo", "visible", True)
        self.setVisible(visible)

        g1 = tm.get("logo", "glow1", {"blur": 80, "color": "rgba(140,180,220,0.24)"})
        self._glow1_effect.setBlurRadius(g1.get("blur", 80))
        self._glow1_effect.setOffset(0, 0)
        r, g, b, a = _parse_rgba(g1.get("color", "rgba(140,180,220,0.24)"))
        self._glow1_effect.setColor(QColor(r, g, b, a))

        g2 = tm.get("logo", "glow2", {"blur": 40, "color": "rgba(160,200,230,0.31)"})
        self._glow2_effect.setBlurRadius(g2.get("blur", 40))
        self._glow2_effect.setOffset(0, 0)
        r, g, b, a = _parse_rgba(g2.get("color", "rgba(160,200,230,0.31)"))
        self._glow2_effect.setColor(QColor(r, g, b, a))

        g3 = tm.get("logo", "glow3", {"blur": 16, "offset_y": 6, "color": "rgba(0,0,0,0.39)"})
        self._glow3_effect.setBlurRadius(g3.get("blur", 16))
        self._glow3_effect.setOffset(0, g3.get("offset_y", 6))
        r, g, b, a = _parse_rgba(g3.get("color", "rgba(0,0,0,0.39)"))
        self._glow3_effect.setColor(QColor(r, g, b, a))

        self._body_start = _parse_rgba(tm.get("logo", "body_color", "rgba(200,220,240,0.43)"))
        self._body_mid = _parse_rgba(tm.get("logo", "body_alt", "rgba(170,200,230,0.29)"))
        self._body_end = _parse_rgba(tm.get("logo", "body_alt", "rgba(170,200,230,0.29)"))
        # Also check for iron-man style body_alt as midpoint
        self._body_end = (max(0, self._body_mid[0]-40), max(0, self._body_mid[1]-30), max(0, self._body_mid[2]-30), self._body_mid[3])
        self.update()

    def _rotate(self):
        self._angle = (self._angle + 0.9) % 360
        self.update()
        self._sync_glow_labels()

    def _sync_glow_labels(self):
        t = QTransform()
        t.translate(100, 100)
        t.rotate(self._angle)
        t.translate(-100, -100)
        for lbl in (self._glow1, self._glow2, self._glow3):
            lbl.setStyleSheet(
                "background:transparent;color:transparent;"
                "font-size:130px;font-family:'Segoe UI';"
            )
            lbl.setText(getattr(self, '_glyph', '❆'))
            lbl.setAlignment(Qt.AlignCenter)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        cx, cy = self.width() / 2, self.height() / 2

        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)

        font = QFont("Segoe UI", getattr(self, '_font_size', 130))
        p.setFont(font)

        grad = QLinearGradient(-65, -65, 65, 65)
        grad.setColorAt(0.0, QColor(*self._body_start))
        grad.setColorAt(0.5, QColor(*self._body_mid))
        grad.setColorAt(1.0, QColor(*self._body_end))
        p.setPen(QPen(QBrush(grad), 1))
        p.drawText(-65, -65, 130, 130, Qt.AlignCenter, getattr(self, '_glyph', '❆'))
        p.restore()

        p.end()
