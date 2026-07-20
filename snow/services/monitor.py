"""System monitor — background CPU/memory/disk collection."""
import threading, time
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemMonitor:
    def __init__(self):
        self._cache = {"cpu": 0, "mem": 0, "mem_used_gb": 0, "mem_total_gb": 0, "disk": 0, "disk_free_gb": 0}
        self._lock = threading.Lock()
        if HAS_PSUTIL:
            threading.Thread(target=self._warm, daemon=True).start()
            threading.Thread(target=self._loop, daemon=True).start()

    def _warm(self):
        try:
            psutil.cpu_percent(interval=1)
        except Exception:
            pass

    def _loop(self):
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                # 动态取 Snow 所在盘符，不硬编码
                drive = (Path(__file__).drive or "C:") + "/"
                disk = psutil.disk_usage(drive)
                with self._lock:
                    self._cache["cpu"] = round(cpu)
                    self._cache["mem"] = round(mem.percent)
                    self._cache["mem_used_gb"] = round(mem.used / 1024**3, 1)
                    self._cache["mem_total_gb"] = round(mem.total / 1024**3, 1)
                    self._cache["disk"] = round(disk.percent)
                    self._cache["disk_free_gb"] = round(disk.free / 1024**3, 1)
            except Exception:
                pass
            time.sleep(2)

    def get(self) -> dict:
        with self._lock:
            return dict(self._cache)
