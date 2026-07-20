"""Glass-morphism card with shadow and hover float effect."""
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor

from snow.theme_manager import get_manager, on_theme_reload


def _parse_rgba(rgba_str: str):
    try:
        s = rgba_str.replace("rgba(", "").replace(")", "")
        parts = [float(x.strip()) for x in s.split(",")]
        return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3] * 255) if len(parts) > 3 else 255)
    except Exception:
        return (0, 0, 0, 180)


class GlassCard(QFrame):
    """Frosted glass card with drop shadow and hover lift animation."""

    def __init__(self, parent=None, width=260, height=360):
        super().__init__(parent)
        self._base_y = 0
        self._card_w = width
        self._card_h = height
        self.setFixedSize(width, height)
        self._apply_style()
        on_theme_reload(self._apply_style)

    def _apply_style(self):
        tm = get_manager()
        bg = tm.get("glass_card", "bg", "rgba(18,18,32,0.7)")
        bd = tm.get("glass_card", "border", "1px solid rgba(255,255,255,0.04)")
        rd = tm.get("glass_card", "radius", "18px")
        self.setStyleSheet(
            f"QFrame{{background:{bg};border-radius:{rd};"
            f"border:{bd};}}"
        )
        # shadow
        sh = tm.get("glass_card", "shadow", {"blur": 60, "offset_y": 20, "color": "rgba(0,0,0,0.71)"})
        if sh:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(sh.get("blur", 60))
            shadow.setOffset(0, sh.get("offset_y", 20))
            r, g, b, a = _parse_rgba(sh.get("color", "rgba(0,0,0,0.71)"))
            shadow.setColor(QColor(r, g, b, a))
            self.setGraphicsEffect(shadow)
        self.repaint()

    def enterEvent(self, event):
        self._base_y = self.y()
        lift = get_manager().get("glass_card", "hover_lift", 6)
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(300)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(self.x(), self._base_y - lift))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    def leaveEvent(self, event):
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(300)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(self.x(), self._base_y))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
