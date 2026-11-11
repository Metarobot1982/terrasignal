"""One-off: find how app.earth2.io reads a location from its URL (lat/lng deep link)."""
import re, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 TERRASIGNAL-probe'}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode('utf-8', 'replace')
base = 'https://app.earth2.io'
h = get(base + '/')
print('html', len(h)); print(h[:1500])
srcs = re.findall(r'<script[^>]+src="([^"]+)"', h)
print('scripts', srcs)
pats = [r'searchParams\.get\(["\'](\w+)', r'[?&#](lat|lng|lon|latitude|longitude|zoom|center)=', r'URLSearchParams', r'["\'](lat|lng)["\']\s*[,:)]',
        r'#thegrid[^"\']{0,60}', r'propertyInfo[^"\']{0,40}', r'flyTo\(', r'location\.hash', r'getParam\w*\(["\'](\w+)']
for s in srcs:
    u = s if s.startswith('http') else base + ('' if s.startswith('/') else '/') + s
    try:
        js = get(u)
    except Exception as e:
        print('fail', u, e); continue
    print('==', u, len(js))
    for p in pats:
        hits = [m for m in re.finditer(p, js)][:6]
        for m in hits:
            a = max(0, m.start() - 160)
            print('[%s]' % p, js[a:m.end() + 160].replace('\n', ' '))
