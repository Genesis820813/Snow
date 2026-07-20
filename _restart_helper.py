"""Snow restart helper — waits for the old instance to exit, then launches main.py."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
time.sleep(3.0)  # 给旧进程足够时间退出（视频停止、TTS 收尾、COM 清理）
try:
    subprocess.Popen(
        [sys.executable, str(ROOT / "main.py")],
        cwd=str(ROOT),
        creationflags=0x08000000,
    )
except Exception as e:
    try:
        with open(ROOT / "diag.log", "a", encoding="utf-8") as f:
            f.write(f"[restart_helper] 重启失败: {e}\n")
    except Exception:
        pass
