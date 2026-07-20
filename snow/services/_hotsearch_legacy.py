"""
hotsearch.py — 百度/微博热搜抓取
被 InfoCard 直接调用，也被 Snow Agent 作为工具使用。
"""

import urllib.request
import urllib.parse
import json
import re
import ssl
from typing import Optional


def fetch_baidu_hotsearch() -> list[dict]:
    """抓取百度实时热搜，返回 [{title, url, rank, hot_score}]"""
    # 百度热搜 API (移动端接口，比 PC 端更稳定)
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://top.baidu.com/",
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[hotsearch] 百度 API 失败: {e}")
        return _fallback_baidu()
    
    cards = data.get("data", {}).get("cards", [])
    results = []
    
    for card in cards:
        if card.get("card_type") != "realtime":
            continue
        content_list = card.get("content", [])
        if not content_list:
            # 可能是嵌套结构
            for sub in card.get("card_list", []):
                content_list.extend(sub.get("content", []))
        
        for item in content_list:
            title = item.get("word") or item.get("query") or ""
            if not title:
                continue
            raw_url = item.get("rawUrl") or item.get("url") or ""
            # 构建搜索链接
            if raw_url and raw_url.startswith("http"):
                link = raw_url
            else:
                link = f"https://www.baidu.com/s?wd={urllib.parse.quote(title)}"
            
            results.append({
                "title": title,
                "url": link,
                "rank": item.get("index", len(results) + 1),
                "hot_score": item.get("hotScore", ""),
                "source": "baidu",
            })
    
    return results[:20]


def _fallback_baidu() -> list[dict]:
    """备用方案：直接解析百度热搜页面 HTML"""
    url = "https://top.baidu.com/board?tab=realtime"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[hotsearch] 备用方案也失败: {e}")
        return []
    
    # 从 HTML 中提取热搜词
    # 百度页面的热搜词通常在 class="c-single-text-ellipsis" 或类似结构中
    titles = re.findall(r'class="c-single-text-ellipsis"[^>]*>([^<]+)<', html)
    if not titles:
        titles = re.findall(r'"word":"([^"]+)"', html)
    if not titles:
        titles = re.findall(r'"query":"([^"]+)"', html)
    
    results = []
    for i, title in enumerate(titles[:20], 1):
        title = title.strip()
        if not title or len(title) < 2:
            continue
        results.append({
            "title": title,
            "url": f"https://www.baidu.com/s?wd={urllib.parse.quote(title)}",
            "rank": i,
            "hot_score": "",
            "source": "baidu",
        })
    
    return results[:20]


def fetch_weibo_hotsearch() -> list[dict]:
    """抓取微博热搜，返回 [{title, url, rank, hot_score}]"""
    # 微博热搜接口（需要 cookie 才能稳定访问）
    url = "https://weibo.com/ajax/side/hotSearch"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://weibo.com/",
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return _fallback_weibo()
    
    realtime = data.get("data", {}).get("realtime", [])
    results = []
    
    for item in realtime[:20]:
        word = item.get("word") or item.get("note") or ""
        if not word:
            continue
        # 微博热搜没有直接 URL，构建搜索链接
        link = f"https://s.weibo.com/weibo?q={urllib.parse.quote(word)}"
        
        results.append({
            "title": word,
            "url": link,
            "rank": item.get("rank", len(results) + 1),
            "hot_score": item.get("num", ""),
            "source": "weibo",
        })
    
    return results


def _fallback_weibo() -> list[dict]:
    """备用：从第三方接口抓微博热搜"""
    # 使用第三方热搜聚合接口
    url = "https://tenapi.cn/v2/weibohot"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    
    if data.get("code") != 200:
        return []
    
    items = data.get("data", [])
    results = []
    for item in items[:8]:
        title = item.get("name", "")
        if not title:
            continue
        results.append({
            "title": title,
            "url": f"https://s.weibo.com/weibo?q={urllib.parse.quote(title)}",
            "rank": len(results) + 1,
            "hot_score": str(item.get("hot", "")),
            "source": "weibo",
        })
    
    return results


def get_hotsearch(source: str = "auto") -> tuple[str, list[dict]]:
    """
    获取热搜，自动选择可用的数据源。
    返回 (source_name, results_list)
    """
    if source in ("baidu", "auto"):
        results = fetch_baidu_hotsearch()
        if results:
            return "baidu", results
    
    if source in ("weibo", "auto"):
        results = fetch_weibo_hotsearch()
        if results:
            return "weibo", results
    
    return "none", []
