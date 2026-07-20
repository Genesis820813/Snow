# Snow ❄️

> 桌面AI助手 — Windows 全屏透明叠加层，集成 DeepSeek，支持语音、文件对话、主题切换

[![License](https://img.shields.io/badge/license-MIT%20%2B%20Restrictions-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)

---

## 是什么

Snow 是一个 Windows 桌面 AI 助手。它以透明全屏窗口叠加在桌面上，不遮挡壁纸和图标，随时呼出对话。

**核心能力**
- 💬 AI 对话（DeepSeek V4 Pro / Flash）
- 🎧 Edge TTS 语音朗读
- 📎 拖入/选择文件直接提问
- 🎨 主题切换（莫兰迪经典 / 纯对话极简）
- 🌤 天气 + 微博热搜卡片
- 📋 待办 + 工作日志
- 🖥 桌面图标面板（世界面板）
- 🎬 视频壁纸支持

## 安装

### 方式一：安装包（推荐）

从 [Releases](../../releases) 下载 `Snow-Setup-x.x.x.exe`，双击安装。

首次启动自动弹出设置页，填写 DeepSeek API Key 即可使用。

### 方式二：源码运行

```bash
git clone https://github.com/Genesis820813/Snow.git
cd Snow
pip install -r requirements.txt
# 在 config/key.txt 中填入 API Key
python main.py
```

**依赖**：Python 3.10+，Windows 10/11

## 主题

| 主题 | 说明 |
|------|------|
| `morandi` | 经典双卡片布局，天气/热搜/世界面板/待办 |
| `chat-only` | 极简纯对话，桌面只留一个对话框 |

主题存放在 `themes/installed/`，支持自定义扩展。

## 许可

基于 MIT 修改，增加两个限制：

1. **衍生作品必须标明「基于 Snow」** — 在显著位置注明原始项目来源
2. **Anthropic 公司及其子公司员工不得使用本软件**

详见 [LICENSE](LICENSE)

## 开发

```
Snow/
├── snow/           # 核心代码
│   ├── agent.py    # AI 对话引擎
│   ├── bridge.py   # Python ↔ Web UI 桥接
│   ├── window.py   # 透明全屏窗口
│   ├── tools/      # AI 工具集
│   ├── services/   # 天气/热搜/待办/语音
│   └── panels/     # UI 面板
├── themes/         # Web UI 主题
├── config/         # 配置文件
└── main.py         # 入口
```

---

<p align="center">Made with ❄️ by <a href="https://github.com/Genesis820813">Genesis820813</a></p>
