"""Research Volcano Engine TTS / Doubao voice models."""
import urllib.request, json, ssl, re

ctx = ssl.create_default_context()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode("utf-8", errors="replace")

def fetch_json(url, timeout=15):
    return json.loads(fetch(url, timeout))

print("=" * 70)
print("1. 火山引擎语音服务产品页")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/product/tts", timeout=10)
    # extract meta description
    m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
    if m: print("  Description:", m.group(1)[:200])
    m = re.search(r'<title>([^<]+)</title>', html)
    if m: print("  Title:", m.group(1))
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("=" * 70)
print("2. 豆包大模型语音API 文档索引")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/docs/6561/125554", timeout=10)
    # find all nav links
    links = re.findall(r'href="(/docs/6561/\d+)[^"]*"[^>]*>([^<]+)</a>', html)
    seen = set()
    for href, title in links[:20]:
        title = title.strip()
        if title and title not in seen and len(title) > 2:
            seen.add(title)
            print(f"  https://www.volcengine.com{href}  ->  {title}")
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("=" * 70)
print("3. 豆包语音 - 流式TTS API (Doubao Streaming TTS)")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/docs/6561/1329505", timeout=10)
    # Find key info
    texts = re.findall(r'<p[^>]*>([^<]{20,200})</p>', html)
    for t in texts[:5]:
        t = t.strip()
        if t and len(t) > 30:
            print(f"  {t[:180]}")
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("=" * 70)
print("4. 豆包语音 - 实时语音对话 (Realtime)")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/docs/6561/1329505", timeout=10)
    sections = re.findall(r'<h[23][^>]*>([^<]+)</h[23]>', html)
    for s in sections[:10]:
        s = s.strip()
        if s:
            print(f"  Section: {s}")
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("=" * 70)
print("5. 豆包语音 - 语音识别 ASR")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/docs/6561/80818", timeout=10)
    m = re.search(r'<title>([^<]+)</title>', html)
    if m: print("  Title:", m.group(1))
except Exception as e:
    print(f"  FAIL: {e}")

print()
print("=" * 70)
print("6. 豆包语音模型定价")
print("=" * 70)
try:
    html = fetch("https://www.volcengine.com/docs/6561/197938", timeout=10)
    prices = re.findall(r'(\d+\.?\d*)\s*(元|/千次|/万字符)', html)
    for p in prices[:8]:
        print(f"  {p}")
except Exception as e:
    print(f"  FAIL: {e}")
