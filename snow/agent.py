"""Snow AI Agent — streaming LLM loop with tool calling and fallback."""
import sys, os, json, urllib.request, urllib.parse, time, re
from pathlib import Path
from PySide6.QtCore import QThread, Signal

from snow.paths import PROJECT_DIR
DATA_DIR = PROJECT_DIR / "data"
KEY_FILE = PROJECT_DIR / "config" / "key.txt"
MODEL_CONFIG_FILE = PROJECT_DIR / "config" / "model_config.json"

MAX_HISTORY = 300
MAX_AGENT_TURNS = 100


def load_model_config():
    defaults = {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
    }
    if MODEL_CONFIG_FILE.exists():
        try:
            cfg = json.loads(MODEL_CONFIG_FILE.read_text(encoding="utf-8"))
            defaults.update(cfg)
        except Exception:
            pass
    return defaults


def read_key():
    if KEY_FILE.exists():
        k = KEY_FILE.read_text(encoding="utf-8-sig").strip()
        if k:
            return k
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return env_key
    return ""


def _diag(msg: str):
    try:
        with open(str(PROJECT_DIR / "diag.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


class SnowAI(QThread):
    token_signal = Signal(str)
    done_signal = Signal(str)
    error_signal = Signal(str)
    tool_signal = Signal(str)
    sentence_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.api_key = read_key()
        self.conversation = []
        self._p = ""
        self._a = True
        self._bridge = None
        self._pending = []  # AI 忙时排队的用户消息

    def ask(self, p):
        if self.isRunning():
            # 上一条还在处理：排队，跑完自动接着处理，不丢消息
            self._pending.append(p)
            return
        self._p = p
        self._a = True
        self.start()

    def stop(self):
        self._a = False
        self._pending.clear()

    def run(self):
        while True:
            self._run_once()
            if self._pending and self._a:
                self._p = self._pending.pop(0)
                continue
            break

    def _run_once(self):
        _diag("[agent] run() started")
        self.api_key = read_key()
        cfg = load_model_config()
        self._provider = cfg.get("provider", "deepseek")
        self._model = cfg.get("model", "deepseek-v4-flash")
        _diag(f"  provider={self._provider}, model={self._model}")

        self._url = cfg.get("api_url", "https://api.deepseek.com/v1/chat/completions")

        if not self.api_key:
            self.error_signal.emit("\u65e0API\u5bc6\u94a5"); return

        from snow.services.memory import load_all as load_memories
        memories = load_memories()
        user_msg = self._p
        if memories:
            memory_lines = "\n".join(f"- {m}" for m in memories)
            user_msg = f"{self._p}\n\n[\u4f60\u7684\u6301\u4e45\u8bb0\u5fc6\uff0c\u8bf7\u53c2\u8003\uff1a]\n{memory_lines}"

        self.conversation.append({"role": "user", "content": user_msg})
        # 裁剪：按条数削减后，确保首条不是孤儿 tool 消息
        # （DeepSeek 不允许首条 role=tool，会 400）
        if len(self.conversation) > MAX_HISTORY:
            self.conversation = self.conversation[-(MAX_HISTORY - 100):]
            while self.conversation and self.conversation[0].get("role") == "tool":
                self.conversation.pop(0)
        self._agent_loop()

    def _agent_loop(self):
        try:
            self._agent_loop_impl()
        except Exception as e:
            import traceback
            _diag(f"[agent] _agent_loop FATAL: {e}\n{traceback.format_exc()}")
            self.error_signal.emit(f"Agent 线程异常: {e}")

    def _agent_loop_impl(self):
        from snow.prompt import build_system_prompt
        from snow.tools.registry import get_tool_defs, execute, get_label

        for _ in range(MAX_AGENT_TURNS):
            if not self._a:
                return
            ctx = self.conversation[-MAX_HISTORY:]
            max_tok = 16384
            system_prompt = build_system_prompt()
            tools = get_tool_defs()

            body = json.dumps({
                "model": self._model,
                "messages": [{"role": "system", "content": system_prompt}] + ctx,
                "tools": tools,
                "stream": True, "max_tokens": max_tok, "temperature": 0.7,
            }, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(self._url, data=body, headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            })

            try:
                _diag(f"[agent] sending request to {self._url} ({len(body)} bytes)")
                full_content = ""
                tool_calls_map = {}
                sentence_buf = ""
                has_tools = False

                _resp_lines = urllib.request.urlopen(req, timeout=90)

                line_count = 0
                for raw_line_bytes in _resp_lines:
                    line_count += 1
                    if not self._a:
                        return
                    line = raw_line_bytes.decode("utf-8", errors="replace").strip()
                    if line_count <= 5:
                        _diag(f"  raw[{line_count}]: {repr(line[:150])}")
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        _diag("  [DONE] received")
                        break
                    try:
                        chunk = json.loads(data_str)
                    except Exception:
                        continue
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta", {})
                    finish = choice.get("finish_reason")

                    content = delta.get("content", "")
                    if content:
                        full_content += content
                        self.token_signal.emit(content)
                        sentence_buf += content
                        while True:
                            m = re.search(r'[\u3002\uff01\uff1f!?.\n]', sentence_buf)
                            if m:
                                sent = sentence_buf[:m.end()].strip()
                                if sent:
                                    self.sentence_signal.emit(sent)
                                sentence_buf = sentence_buf[m.end():]
                            else:
                                break

                    if "tool_calls" in delta:
                        has_tools = True
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_map:
                                tool_calls_map[idx] = {"id": tc.get("id", f"call_{idx}"), "name": "", "arguments": ""}
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                tool_calls_map[idx]["name"] = fn["name"]
                            if fn.get("arguments"):
                                tool_calls_map[idx]["arguments"] += fn["arguments"]

                    if finish:
                        _diag(f"  finish_reason={finish}")
                        break

                if sentence_buf.strip():
                    self.sentence_signal.emit(sentence_buf.strip())

                _diag(f"  stream done, content={len(full_content)} chars, tools={has_tools}, lines={line_count}")

                if has_tools and tool_calls_map:
                    msg = {"role": "assistant", "content": full_content}
                    msg["tool_calls"] = [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                        for tc in tool_calls_map.values()
                    ]
                    self.conversation.append(msg)

                    for tc in tool_calls_map.values():
                        tool_name = tc["name"]
                        try:
                            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                        except Exception:
                            args = {}

                        label = get_label(tool_name, args)
                        self.tool_signal.emit(label)

                        result = execute(tool_name, args)
                        self.conversation.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)[:32000]})

                        result_str = str(result)
                        if tool_name == "desktop_summary":
                            try:
                                count = len(json.loads(result_str))
                                self.tool_signal.emit(f"  \u21b3 \u627e\u5230 {count} \u4e2a\u5e94\u7528")
                            except Exception:
                                self.tool_signal.emit("  \u21b3 \u5b8c\u6210")
                        elif tool_name == "show_world_icons":
                            if "\u65e0\u9057\u6f0f" in result_str:
                                self.tool_signal.emit("  \u21b3 \u6e32\u67d3\u5b8c\u6210 \u2713")
                            else:
                                self.tool_signal.emit("  \u21b3 \u5b8c\u6210")
                        else:
                            summary = result_str[:35].replace("\n", " ").strip()
                            if summary:
                                self.tool_signal.emit(f"  \u21b3 {summary}")
                    continue

                if full_content:
                    self.conversation.append({"role": "assistant", "content": full_content})
                self.done_signal.emit(full_content)
                return

            except urllib.error.HTTPError as e:
                _diag(f"  HTTPError: {e.code} {e.reason}")
                err_body = e.read().decode(errors="replace")[:500]
                self.error_signal.emit(f"HTTP {e.code}: {e.reason}\n{err_body}")
                return
            except TimeoutError:
                _diag("  TimeoutError")
                self.error_signal.emit("\u8bf7\u6c42\u8d85\u65f6\uff0c\u8bf7\u68c0\u67e5\u7f51\u7edc\u540e\u91cd\u8bd5")
                return
            except Exception as e:
                _diag(f"  Exception: {e}")
                err_msg = str(e)
                if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
                    self.error_signal.emit("\u8bf7\u6c42\u8d85\u65f6\uff0c\u8bf7\u68c0\u67e5\u7f51\u7edc\u540e\u91cd\u8bd5")
                    return
                if any(kw in err_msg.lower() for kw in [
                    "connection", "refused", "unreachable", "getaddrinfo",
                    "name or service not known", "network", "eof", "reset",
                ]):
                    self.error_signal.emit(f"\u7f51\u7edc\u8fde\u63a5\u5931\u8d25: {err_msg[:60]}")
                    return
                self.error_signal.emit(err_msg)
                return
        self.error_signal.emit("⚠ 思考轮次达到上限（100轮），任务可能未完成。请简化任务或分步进行。")
