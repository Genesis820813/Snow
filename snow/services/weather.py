"""Weather service — ip-api.com geolocation + wttr.in forecast, 10-minute cache."""
import json, time, urllib.request, ssl, urllib.parse
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent


def get_weather() -> dict:
    cache_file = PROJECT_DIR / "data" / "weather_cache.json"
    now = time.time()
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            if now - cache.get("ts", 0) < 600:
                return cache["data"]
        except Exception:
            pass  # 缓存损坏：当作过期，重新拉取

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    city = "Shenzhen"
    city_cn = "\u6df1\u5733"
    # 手动指定城市：data/city.txt 存在则优先使用，不做 IP 定位（挂代理时 IP 定位会飘）
    city_file = PROJECT_DIR / "data" / "city.txt"
    manual_city = ""
    if city_file.exists():
        try:
            manual_city = city_file.read_text(encoding="utf-8").strip().split("\n")[0]
        except Exception:
            manual_city = ""
    if manual_city:
        city = manual_city
        city_cn = manual_city
    else:
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?lang=zh-CN",
                headers={"User-Agent": "curl/8.0"}
            )
            resp = urllib.request.urlopen(req, timeout=5, context=ctx)
            ip_data = json.loads(resp.read().decode("utf-8"))
            if ip_data.get("status") == "success":
                city = ip_data.get("city", "Shenzhen")
                city_cn = ip_data.get("city", "\u6df1\u5733")
                if not city:
                    city = ip_data.get("regionName", "Shenzhen")
                    city_cn = city
        except Exception as e:
            print(f"[Weather] geolocation failed: {e}", flush=True)

    city_enc = urllib.parse.quote(city)
    d = None
    for attempt, (scheme, ua) in enumerate([
        ("https", "curl/8.0"),
        ("https", "Mozilla/5.0"),
        ("http", "curl/8.0"),
    ]):
        try:
            url = f"{scheme}://wttr.in/{city_enc}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            resp = urllib.request.urlopen(req, timeout=8, context=ctx)
            raw = resp.read()
            if raw and raw.strip():
                d = json.loads(raw.decode("utf-8"))
                break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)
            continue

    if d is None:
        # 全部重试耗尽：刷新缓存 ts 避免频繁重试
        _write_weather_cache(cache_file, now, None)
        raise RuntimeError("weather fetch exhausted all retries")

    cc = d["current_condition"][0]
    desc = cc["weatherDesc"][0]["value"]
    nearest = d.get("nearest_area", [{}])[0]
    wttr_city = nearest.get("areaName", [{}])[0].get("value", city)
    display_city = city_cn if city_cn else wttr_city

    desc_lower = desc.lower()
    if "rain" in desc_lower or "drizzle" in desc_lower or "shower" in desc_lower:
        icon = "\U0001f327"
    elif "thunder" in desc_lower or "storm" in desc_lower:
        icon = "\u26c8"
    elif "snow" in desc_lower:
        icon = "\u2744"
    elif "fog" in desc_lower or "mist" in desc_lower or "haze" in desc_lower:
        icon = "\U0001f32b"
    elif "cloud" in desc_lower or "overcast" in desc_lower:
        icon = "\u2601"
    elif "sun" in desc_lower or "clear" in desc_lower:
        icon = "\u2600"
    elif "partly" in desc_lower:
        icon = "\u26c5"
    else:
        icon = "\u2600"

    data = {
        "icon": icon,
        "temp": f"{cc['temp_C']}\u00b0",
        "city": f"{display_city} \u00b7 {desc}",
    }
    _write_weather_cache(cache_file, now, data)
    return data


def _write_weather_cache(cache_file, ts, data):
    """写缓存。data=None 时仅刷新 ts（失败节流，下次请求至少等缓存过期）。"""
    try:
        (PROJECT_DIR / "data").mkdir(exist_ok=True)
        payload = {"ts": ts, "data": data}
        cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
