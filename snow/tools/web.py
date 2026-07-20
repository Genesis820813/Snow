"""Tool: web operations — open_url, search_web (真实抓取，返回结果给AI)."""
import re
import ssl
import subprocess
import urllib.parse
import urllib.request

TOOLS = [
    ("open_url", "打开网页", {"url": ("string", "URL")}, ["url"]),
    ("search_web", "搜索网络并返回结果摘要（标题+链接+简介），供你阅读和引用",
     {"query": ("string", "关键词")}, ["query"]),
]

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _open_url(args):
    url = args.get("url", "")
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.Popen(["cmd", "/c", "start", url], shell=True, creationflags=0x08000000)
    return f"已打开: {url}"


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text).strip()


def _fetch(url: str, timeout: int = 10) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9",
    })
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode("utf-8", errors="replace")


def _search_sogou(query: str) -> list:
    html = _fetch("https://www.sogou.com/web?query=" + urllib.parse.quote(query))
    out = []
    for link, title in re.findall(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)[:6]:
        if link.startswith("/"):
            link = "https://www.sogou.com" + link
        out.append((_strip_tags(title), link, ""))
    return out


def _search_ddg(query: str) -> list:
    html = _fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    out = []
    blocks = re.findall(r'<div class="result[^"]*">(.*?)(?=<div class="result|$)', html, re.S)[:6]
    for b in blocks:
        m = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        if not m:
            continue
        m_s = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', b, re.S)
        out.append((_strip_tags(m.group(2)), m.group(1), _strip_tags(m_s.group(1))[:150] if m_s else ""))
    return out


def _search_web(args):
    query = args.get("query", "")
    if not query:
        return "关键词为空"

    results, engine = [], ""
    for name, fn in [("搜狗", _search_sogou), ("DuckDuckGo", _search_ddg)]:
        try:
            results = fn(query)
            if results:
                engine = name
                break
        except Exception:
            continue

    if not results:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        subprocess.Popen(["cmd", "/c", "start", url], shell=True, creationflags=0x08000000)
        return "搜索引擎抓取失败，已为用户打开浏览器搜索页。注意：你没有拿到结果内容。"

    lines = []
    for i, (title, link, snippet) in enumerate(results, 1):
        item = f"{i}. {title}\n   {link}"
        if snippet:
            item += f"\n   {snippet}"
        lines.append(item)
    return f"搜索「{query}」({engine}) 结果:\n\n" + "\n\n".join(lines)


HANDLERS = {
    "open_url": _open_url,
    "search_web": _search_web,
}
