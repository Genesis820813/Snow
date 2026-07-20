"""Edge TTS 子进程脚本 — 避免 asyncio 跨线程问题"""
import sys, edge_tts, asyncio

text = sys.argv[1]
voice = sys.argv[2]
out = sys.argv[3]

async def main():
    comm = edge_tts.Communicate(text, voice)
    await comm.save(out)

asyncio.run(main())
