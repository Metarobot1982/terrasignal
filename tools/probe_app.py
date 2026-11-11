"""One-off: find the public endpoints behind the app's countdown banners, territories and skin store."""
import re, urllib.request, json
UA = {'User-Agent': 'Mozilla/5.0 TERRASIGNAL-probe', 'Accept': 'application/json'}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode('utf-8', 'replace')
js = get('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js')
for p in [r'[Cc]ountdown\w*', r'[Bb]anner\w*', r'territor\w*', r'skin\w*', r'newsTicker\w*']:
    names = sorted(set(re.findall(p, js)))[:40]
    print(p, names)
paths = sorted(set(re.findall(r'["\'`](/(?:api|v\d|countdown|banners?|territor|skins?|news|ticker|marketplace|governance)[^"\'`\s]{0,80})["\'`]', js)))
print('PATHS', len(paths)); print('\n'.join(paths[:300]))
for k in ['r.earth2.io', 'api.earth2.io', 'baseURL', 'apiUrl', 'API_URL']:
    for m in list(re.finditer(re.escape(k), js))[:4]:
        print('[%s]' % k, js[max(0, m.start()-150):m.end()+150].replace('\n', ' '))
for m in list(re.finditer(r'countdown', js, re.I))[:12]:
    print('[cd]', js[max(0, m.start()-200):m.end()+200].replace('\n', ' '))
