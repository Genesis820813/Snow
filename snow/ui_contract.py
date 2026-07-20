"""
Snow UI Contract V1 — Snow ↔ UI 之间的契约。

这不是通信协议（QWebChannel 才是），而是声明：
- Snow 提供哪些数据和方法给 UI
- Snow 会主动推送哪些信号给 UI
- UI 需要声明自己依赖哪些接口

UI 作者只需看这个文件，不需要读 agent/bridge/services。
"""
from __future__ import annotations

CONTRACT_VERSION = "1.0"

# ── Snow 提供的数据接口（UI 通过 QWebChannel 调用 bridge Slot） ──

METHODS: dict[str, dict] = {
    # AI 对话
    "ask":              {"args": [{"name": "text", "type": "str"}],    "returns": None,  "group": "chat"},
    # 天气
    "get_weather":      {"args": [],                                    "returns": "str", "group": "weather"},
    # 热搜
    "get_hotsearch":    {"args": [],                                    "returns": "str", "group": "news"},
    # 待办
    "get_todos":        {"args": [],                                    "returns": "str", "group": "todo"},
    "add_todo":         {"args": [{"name": "text", "type": "str"}],    "returns": None,  "group": "todo"},
    "toggle_todo":      {"args": [{"name": "idx", "type": "int"}],     "returns": None,  "group": "todo"},
    "remove_todo":      {"args": [{"name": "idx", "type": "int"}],     "returns": None,  "group": "todo"},
    # TTS
    "speak":            {"args": [{"name": "text", "type": "str"}],    "returns": None,  "group": "tts"},
    "toggle_tts":       {"args": [],                                    "returns": "bool","group": "tts"},
    "get_voice":        {"args": [],                                    "returns": "str", "group": "tts"},
    "get_voices":       {"args": [],                                    "returns": "str", "group": "tts"},
    "set_voice":        {"args": [{"name": "voice", "type": "str"}],   "returns": None,  "group": "tts"},
    # 模型
    "get_model_config": {"args": [],                                    "returns": "str", "group": "model"},
    "switch_model":     {"args": [{"name": "provider", "type": "str"}, {"name": "model", "type": "str"}],
                                                                        "returns": None,  "group": "model"},
    # 世界面板
    "get_apps":         {"args": [],                                    "returns": "str", "group": "world"},
    "launch_app":       {"args": [{"name": "name", "type": "str"}],    "returns": None,  "group": "world"},
    "close_world":      {"args": [],                                    "returns": None,  "group": "world"},
    "toggle_world":     {"args": [],                                    "returns": None,  "group": "world"},
    # 工作日志
    "get_work_log":     {"args": [],                                    "returns": "str", "group": "work"},
    "record_work":      {"args": [{"name": "action", "type": "str"}, {"name": "status", "type": "str"}],
                                                                        "returns": None,  "group": "work"},
    # 系统
    "get_system_stats": {"args": [],                                    "returns": "str", "group": "system"},
    # 文件 / 设置 / 退出
    "open_settings":    {"args": [],                                    "returns": None,  "group": "system"},
    "pick_file":        {"args": [],                                    "returns": "str", "group": "system"},
    "save_uploaded_file":{"args": [{"name": "name", "type": "str"}, {"name": "b64data", "type": "str"}],
                                                                        "returns": "str", "group": "system"},
    "exit_snow":        {"args": [],                                    "returns": None,  "group": "system"},
    # UI 管理
    "get_ui_list":      {"args": [],                                    "returns": "str", "group": "ui"},
    "switch_ui":        {"args": [{"name": "name", "type": "str"}],    "returns": None,  "group": "ui"},
}

# ── Snow 主动推送的信号（UI 通过 QWebChannel 监听 Signal） ──

SIGNALS: dict[str, dict] = {
    "ai_token":         {"type": "str",  "group": "chat",    "desc": "AI 逐字流式输出"},
    "ai_done":          {"type": "str",  "group": "chat",    "desc": "AI 本轮完成"},
    "ai_error":         {"type": "str",  "group": "chat",    "desc": "AI 出错"},
    "ai_sentence":      {"type": "str",  "group": "chat",    "desc": "AI 完整句子（TTS用）"},
    "ai_work":          {"type": "str",  "group": "work",    "desc": "AI 工具调用标签"},
    "state_changed":    {"type": "str",  "group": "system",  "desc": "模型/TTS 状态变更"},
    "todos_changed":    {"type": None,   "group": "todo",    "desc": "待办列表变更"},
    "world_closed":     {"type": None,   "group": "world",   "desc": "世界面板关闭"},
    "world_show":       {"type": "object","group": "world",  "desc": "世界面板渲染数据"},
    "world_toggle":     {"type": None,   "group": "world",   "desc": "世界面板切换"},
    "exit_requested":   {"type": None,   "group": "system",  "desc": "退出请求"},
    "file_picked":      {"type": "str",  "group": "system",  "desc": "文件选择结果"},
    "apps_loaded":      {"type": "str",  "group": "world",   "desc": "应用列表加载完成"},
}

# ── 功能分组（UI 可按组声明依赖） ──

CAPABILITIES = sorted(set(info["group"] for info in {**METHODS, **SIGNALS}.values()))

def validate_manifest_requires(requires: list[str]) -> list[str]:
    """校验 manifest 中声明的 requires 是否都在 METHODS 中。返回缺失的接口名。"""
    known = set(METHODS.keys()) | set(SIGNALS.keys())
    return [r for r in requires if r not in known]

def version_compatible(requested: str) -> bool:
    """检查 UI 要求的版本是否兼容当前 CONTRACT_VERSION。"""
    # V1: 简单的主版本号匹配
    return requested.split(".")[0] == CONTRACT_VERSION.split(".")[0]
