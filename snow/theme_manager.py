"""Theme Manager — 读取主题 panel.json，为所有组件提供配色数据。

单例。组件通过 ThemeManager.get(section, key) 获取颜色。
切换主题时调用 ThemeManager.load(theme_name) 重新加载。
"""

import json
from pathlib import Path

from snow.paths import PROJECT_DIR
THEMES_DIR = PROJECT_DIR / "themes" / "installed"

_instance = None
_reload_callbacks = []


def on_theme_reload(callback):
    """注册回调：主题切换时自动调用。callback() 无参数。"""
    _reload_callbacks.append(callback)


def _fire_reload():
    for cb in _reload_callbacks:
        try:
            cb()
        except Exception as e:
            print(f"[ThemeManager] callback error: {e}")

# 莫兰迪默认值 — 当主题缺少某些 key 时的后备
_DEFAULTS = {
    "_layout": {
        "card_w": 260, "card_h": 380,
        "gap": 8,
        "left_x": 22, "left_y": "auto_bottom",
        "right_x": "auto_right", "right_y": "auto_bottom",
    },
    "background": {
        "top": "#7a8f9e",
        "bottom": "#58695e",
        "split_ratio": 0.4,
    },
    "glass_card": {
        "bg": "rgba(18,18,32,0.7)",
        "border": "1px solid rgba(255,255,255,0.04)",
        "radius": "18px",
        "shadow": {"blur": 60, "offset_y": 20, "color": "rgba(0,0,0,0.71)"},
    },
    "left_card": {
        "section_title": "rgba(255,255,255,0.28)",
        "weather_temp": "rgba(255,255,255,0.92)",
        "weather_date": "rgba(255,255,255,0.68)",
        "weather_city": "rgba(255,255,255,0.30)",
        "time": "rgba(255,255,255,0.60)",
        "divider": "rgba(255,255,255,0.08)",
        "hotsearch_num": "rgba(255,120,100,0.55)",
        "hotsearch_text": "rgba(255,255,255,0.40)",
        "hotsearch_fire": "rgba(255,140,80,0.65)",
        "refresh_btn_bg": "rgba(255,255,255,0.05)",
        "refresh_btn_text": "rgba(255,255,255,0.25)",
        "refresh_btn_hover_bg": "rgba(255,255,255,0.12)",
        "refresh_btn_hover_text": "rgba(255,255,255,0.50)",
    },
    "right_card": {
        "section_title": "rgba(255,255,255,0.28)",
        "ai_work_primary": "rgba(100,200,160,0.85)",
        "ai_work_secondary": "rgba(180,180,180,0.70)",
        "ai_work_done": "rgba(255,255,255,0.15)",
        "divider": "rgba(255,255,255,0.08)",
        "todo_normal": "rgba(255,255,255,0.35)",
        "todo_done": "rgba(255,255,255,0.15)",
        "scrollbar_thumb": "rgba(255,255,255,0.08)",
    },
    "world_panel": {
        "toggle_btn_bg": "rgba(22,22,40,0.9)",
        "toggle_btn_text": "rgba(255,255,255,0.7)",
        "toggle_btn_border": "1px solid rgba(255,255,255,0.08)",
        "toggle_btn_radius": "22px",
        "toggle_active_bg": "rgba(100,160,220,0.25)",
        "toggle_active_border": "1px solid rgba(100,160,220,0.3)",
        "toggle_shadow": {"blur": 30, "offset_y": 8, "color": "rgba(0,0,0,0.71)"},
        "toggle_hover_glow": "rgba(100,160,220,0.2)",
        "icon_bg": "rgba(22,22,40,0.9)",
        "icon_text": "rgba(255,255,255,0.5)",
        "icon_border": "1px solid rgba(255,255,255,0.06)",
        "icon_radius": "10px",
        "icon_hover_bg": "rgba(30,30,50,0.95)",
        "icon_hover_text": "#ffffff",
        "icon_shadow": {"blur": 14, "offset_y": 3, "color": "rgba(0,0,0,0.39)"},
        "icon_colors": ["#1a73e8", "#e4405f", "#25d366", "#ff8c00", "#5c2d91", "#0088cc", "#ff4500", "#db4437"],
    },
    "settings": {
        "bg": "#1e2a2a",
        "sidebar_bg": "#162020",
        "text_primary": "rgba(255,255,255,0.85)",
        "text_dim": "rgba(255,255,255,0.40)",
        "text_faint": "rgba(255,255,255,0.20)",
        "card_bg": "rgba(255,255,255,0.05)",
        "input_bg": "rgba(255,255,255,0.06)",
        "input_focus_bg": "rgba(255,255,255,0.10)",
        "btn_bg": "rgba(255,255,255,0.08)",
        "btn_hover_bg": "rgba(255,255,255,0.14)",
        "accent": "#64b4a0",
        "accent_hover": "rgba(100,180,160,0.4)",
        "nav_active_bg": "rgba(100,180,160,0.15)",
        "nav_hover_bg": "rgba(255,255,255,0.04)",
        "combo_dropdown_bg": "#1a2828",
        "border_radius": "12px",
        "small_radius": "6px",
        "scrollbar_thumb": "rgba(255,255,255,0.08)",
    },
    "logo": {
        "glyph": "❆",
        "width": 200,
        "height": 200,
        "font_size": 130,
        "rotate": True,
        "visible": True,
        "body_color": "rgba(200,220,240,0.43)",
        "body_alt": "rgba(170,200,230,0.29)",
        "glow1": {"blur": 80, "color": "rgba(140,180,220,0.24)"},
        "glow2": {"blur": 40, "color": "rgba(160,200,230,0.31)"},
        "glow3": {"blur": 16, "color": "rgba(0,0,0,0.39)", "offset_y": 6},
    },
    "close_button": {
        "bg": "rgba(255,255,255,0.05)",
        "text": "rgba(255,255,255,0.20)",
        "hover_bg": "rgba(220,50,50,0.3)",
        "hover_text": "#ffffff",
    },
}


class ThemeManager:
    def __init__(self):
        self._data = dict(_DEFAULTS)  # 深拷贝
        for k, v in _DEFAULTS.items():
            if isinstance(v, dict):
                self._data[k] = dict(v)
        self._current = "morandi"

    def load(self, name: str) -> bool:
        panel_path = THEMES_DIR / name / "panel.json"
        if not panel_path.exists():
            # 没有 panel.json → 重置为默认（莫兰迪）
            self._data = {}
            for k, v in _DEFAULTS.items():
                if isinstance(v, dict):
                    self._data[k] = dict(v)
            self._current = name
            print(f"[ThemeManager] no panel.json for {name}, reset to defaults")
            _fire_reload()
            return True

        try:
            loaded = json.loads(panel_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ThemeManager] failed to load {name}: {e}")
            return False

        # 合并：先重置为默认值，再用新主题覆盖（防止旧主题残留 key）
        self._data = {}
        for k, v in _DEFAULTS.items():
            if isinstance(v, dict):
                self._data[k] = dict(v)
        for section in _DEFAULTS:
            if section in loaded and isinstance(loaded[section], dict):
                for k, v in loaded[section].items():
                    self._data[section][k] = v

        self._current = name
        print(f"[ThemeManager] loaded {name}")
        _fire_reload()
        return True

    def get(self, section: str, key: str, default=None):
        """获取配色值。section='background', key='top'"""
        sec = self._data.get(section, {})
        return sec.get(key, default)

    def get_section(self, section: str) -> dict:
        """获取整个section的配色"""
        return dict(self._data.get(section, {}))

    @property
    def current(self) -> str:
        return self._current


def get_manager() -> ThemeManager:
    global _instance
    if _instance is None:
        _instance = ThemeManager()
    return _instance
