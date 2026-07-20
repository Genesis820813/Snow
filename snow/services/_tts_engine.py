"""
Snow TTS — Edge TTS (在线合成，子进程隔离 asyncio)
"""
import sys, tempfile, uuid, subprocess
from pathlib import Path

# ── Edge TTS 音色 ──
EDGE_VOICES = {
    "Xiaoxiao": "zh-CN-XiaoxiaoNeural",   # 女声 活泼
    "Yunxi":    "zh-CN-YunxiNeural",       # 男声 自然
    "Xiaoyi":   "zh-CN-XiaoyiNeural",      # 女声 温柔
}
EDGE_VOICE_LIST = list(EDGE_VOICES.keys())
DEFAULT_VOICE = "Xiaoxiao"
ALL_VOICES = EDGE_VOICE_LIST


def _edge_generate(text: str, voice: str):
    """Edge TTS 生成——内联 asyncio，不依赖子进程（兼容 PyInstaller 打包）。"""
    import asyncio
    import edge_tts

    short_name = EDGE_VOICES.get(voice, "zh-CN-XiaoxiaoNeural")
    out_path = str(Path(tempfile.gettempdir()) / f"snow_edge_{uuid.uuid4().hex[:8]}.mp3")

    async def _gen():
        comm = edge_tts.Communicate(text, short_name)
        await comm.save(out_path)

    try:
        asyncio.run(_gen())
    except Exception as e:
        print(f"[TTS Edge] 失败: {e}", flush=True)
        return None

    if not Path(out_path).exists():
        return None
    return out_path
