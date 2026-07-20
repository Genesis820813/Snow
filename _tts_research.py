import urllib.request, json, ssl, re

ctx = ssl.create_default_context()

def get(url, timeout=12):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'curl/8.0',
        'Accept': 'application/json, text/plain, */*'
    })
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        ct = r.headers.get('Content-Type', '')
        data = r.read()
        if 'json' in ct:
            return json.loads(data)
        return data.decode('utf-8', errors='replace')
    except Exception as e:
        return 'ERR: ' + str(e)

# Try multiple URLs
urls = [
    ('产品页', 'https://www.volcengine.com/product/tts'),
    ('API总览', 'https://www.volcengine.com/docs/6561/79820'),
    ('流式TTS', 'https://www.volcengine.com/docs/6561/79823'),
    ('豆包语音模型列表', 'https://www.volcengine.com/docs/6561/125554'),
    ('实时语音对话', 'https://www.volcengine.com/docs/6561/1329505'),
    ('定价', 'https://www.volcengine.com/docs/6561/197938'),
    ('SDK', 'https://github.com/volcengine/volc-sdk-python'),
]

for label, url in urls:
    print(f'\n{"="*60}')
    print(f'  {label}: {url}')
    print(f'{"="*60}')
    r = get(url)
    if isinstance(r, str) and r.startswith('ERR'):
        print(f'  {r}')
    elif isinstance(r, str):
        # Try to extract title and description
        t = re.findall(r'<title>([^<]+)</title>', r)
        if t: print(f'  Title: {t[0]}')
        d = re.findall(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', r)
        if d: print(f'  Desc: {d[0][:200]}')
        # Try to find key sections
        h2s = re.findall(r'<h2[^>]*>([^<]+)</h2>', r)
        if h2s:
            print('  Sections:')
            for h in h2s[:8]:
                print(f'    - {h.strip()}')
        h3s = re.findall(r'<h3[^>]*>([^<]+)</h3>', r)
        if h3s:
            print('  Subsections:')
            for h in h3s[:8]:
                print(f'    - {h.strip()}')
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2)[:2000])
