"""TTS state machine — sentence queue → generate WAV → play pipeline."""
import json, threading, subprocess, time, sys, re, os, shutil, tempfile, glob
from pathlib import Path

from snow.paths import PROJECT_DIR

_HAS_FFPLAY = shutil.which("ffplay") is not None


def _player_cmd(path: str) -> list:
    """音频播放命令：优先 ffplay（快），没有则用 Windows 自带 PowerShell MediaPlayer（零依赖）。"""
    if _HAS_FFPLAY:
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
    uri = Path(path).resolve().as_uri()
    ps = ("Add-Type -AssemblyName presentationCore;"
          "$p=New-Object System.Windows.Media.MediaPlayer;"
          f"$p.Open('{uri}');$p.Play();"
          "$t=0;while(-not $p.NaturalDuration.HasTimeSpan -and $t -lt 60){Start-Sleep -m 100;$t++};"
          "if($p.NaturalDuration.HasTimeSpan){$d=$p.NaturalDuration.TimeSpan.TotalMilliseconds;"
          "while($p.Position.TotalMilliseconds -lt $d){Start-Sleep -m 150}};"
          "$p.Stop();$p.Close()")
    return ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps]


def _sweep_temp_audio():
    """清理历史遗留的 TTS 临时音频。"""
    tmp = tempfile.gettempdir()
    for pattern in ("snow_edge_*.mp3", "snow_tts_*.wav"):
        for f in glob.glob(os.path.join(tmp, pattern)):
            try:
                os.remove(f)
            except Exception:
                pass

# 非文字字符——emoji、图标、箭头、几何图形、装饰符号。TTS 一律不读。
_NON_SPEECH_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emoji 主区（表情、物品、动物、符号…）
    "\U0001FB00-\U0001FBFF"   # legacy computing symbols
    "\u2190-\u21FF"           # 箭头 → ←
    "\u2300-\u23FF"           # 技术符号 ⌚ ⏰
    "\u2460-\u24FF"           # 带圈数字 ①②
    "\u2500-\u259F"           # 制表符 ─ ━ ▓
    "\u25A0-\u25FF"           # 几何图形 ■ ▲ ●
    "\u2600-\u27BF"           # 杂项符号+装饰符 ★ ☆ ✅ ❌ ✕ 🔧(部分)
    "\u2B00-\u2BFF"           # 杂项符号和箭头 ⬆ ⭐
    "\u2022\u2023\u25E6"      # 项目符号 •
    "\uFE00-\uFE0F"           # 变体选择符
    "\u200B-\u200D\uFEFF"     # 零宽字符
    "\U0001F1E6-\U0001F1FF"   # 区域指示符（旗帜）
    "]+"
)


def strip_non_speech(text: str) -> str:
    """去掉所有不该读出来的图标/emoji/装饰字符，只留真正的文字。"""
    cleaned = _NON_SPEECH_RE.sub("", text)
    return re.sub(r"  +", " ", cleaned)

_tts_engine = None
_tts_engine_lock = threading.Lock()


class TTSEngine:
    """TTS state machine — ribbon_chat pattern: generate all → play all."""

    def __init__(self):
        self.enabled = True
        self._wavs = []
        self._wav_idx = 0
        self._sentence_queue = []
        self._queue_lock = threading.Lock()
        self._generating = False
        self._playing = False
        self._waiting = False
        self._stream_done = False
        self._process = None
        self._process_lock = threading.Lock()
        self._last_queued = ""
        threading.Thread(target=_sweep_temp_audio, daemon=True).start()

    def speak(self, text: str):
        text = strip_non_speech(text or "")
        safe = text.encode("gbk", errors="replace").decode("gbk")
        print(f"[TTS] speak() queued: {safe[:50]}...", flush=True)
        if not text or not text.strip():
            return
        t = text.strip()
        self._last_queued = t
        with self._queue_lock:
            self._sentence_queue.append(t)
            if not self._generating:
                self._generating = True
                start_thread = True
            else:
                start_thread = False
        if start_thread:
            threading.Thread(target=self._generate_all, daemon=True).start()

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled:
            self._stop_playback()
        else:
            with self._queue_lock:
                has_wavs = self._wav_idx < len(self._wavs)
            if has_wavs:
                self._playing = True
                threading.Thread(target=self._play_all, daemon=True).start()
            elif self._last_queued:
                self.speak(self._last_queued)
        return self.enabled

    def _generate_all(self):
        self._stream_done = False
        with self._queue_lock:
            self._wavs.clear()
            self._wav_idx = 0
        try:
            from snow.services._tts_engine import EDGE_VOICES, DEFAULT_VOICE
            voice = DEFAULT_VOICE
            vf = PROJECT_DIR / "data" / "voice.txt"
            if vf.exists():
                v = vf.read_text(encoding="utf-8").strip().split("\n")[0]
                if v:
                    voice = v
            if voice not in EDGE_VOICES:
                voice = DEFAULT_VOICE
            print(f"[TTS] voice={voice} (Edge)", flush=True)

            while True:
                with self._queue_lock:
                    if not self._sentence_queue:
                        break
                    text = self._sentence_queue.pop(0)

                try:
                    from snow.services._tts_engine import _edge_generate
                    wav = _edge_generate(text, voice)
                except Exception:
                    import traceback; traceback.print_exc()
                    continue
                if not wav:
                    continue  # 合成失败：跳过该句，不入播放队列

                with self._queue_lock:
                    self._wavs.append(wav)
                    # 首句到达即启动播放；_waiting 收尾。加 _playing 检查防双重启动。
                    need_start = not self._playing and self.enabled and (len(self._wavs) == 1 or self._waiting)
                    if self._waiting:
                        self._waiting = False
                if need_start:
                    self._playing = True
                    threading.Thread(target=self._play_all, daemon=True).start()
        finally:
            self._generating = False
            self._stream_done = True
            if self._waiting:
                self._waiting = False
                if not self._playing and self.enabled:
                    self._playing = True
                    threading.Thread(target=self._play_all, daemon=True).start()

    def _play_all(self):
        while True:
            with self._queue_lock:
                if self._wav_idx >= len(self._wavs):
                    if self._stream_done:
                        self._playing = False
                        return
                    else:
                        self._waiting = True
                        return
                wav = self._wavs[self._wav_idx]
                self._wav_idx += 1

            self._play_wav(wav)
            if not self._playing:
                return

    def _play_wav(self, wav: str):
        proc = None
        try:
            proc = subprocess.Popen(
                _player_cmd(wav),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=0x08000000,
            )
            with self._process_lock:
                self._process = proc
            proc.wait()
        except Exception:
            pass
        finally:
            with self._process_lock:
                if self._process is proc:
                    self._process = None
            try:
                os.remove(wav)  # 播完即删，不留临时文件
            except Exception:
                pass

    def _stop_playback(self):
        self._playing = False
        self._generating = False
        self._waiting = False
        with self._queue_lock:
            self._sentence_queue.clear()
            # 清理残留 wav 文件，避免磁盘堆积
            for w in self._wavs[self._wav_idx:]:
                try:
                    os.remove(w)
                except Exception:
                    pass
            self._wavs.clear()
            self._wav_idx = 0
        with self._process_lock:
            proc = self._process
            self._process = None
        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass

    def get_voices(self) -> list:
        try:
            from snow.services._tts_engine import ALL_VOICES
            return list(ALL_VOICES)
        except Exception:
            return ["Xiaoxiao", "Yunxi", "Xiaoyi"]
