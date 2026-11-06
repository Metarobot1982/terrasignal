import re, urllib.request
UA = 'Mozilla/5.0 (compatible; TERRASIGNAL-probe/1.0)'
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=30).read().decode('utf-8', 'replace')
h = get('https://earth2.io/news')
srcs = re.findall(r'src="([^"]+\.js)"', h)
print('scripts', srcs)
for s in srcs:
    u = s if s.startswith('http') else 'https://earth2.io' + s
    js = get(u)
    print('==', u, len(js))
    urls = sorted(set(re.findall(r'https?://[a-zA-Z0-9.\-]+(?:/[a-zA-Z0-9_\-./{}$]*)?', js)))
    print('urls:', [x for x in urls if not re.search(r'w3\.org|reactjs|github\.com/facebook', x)][:120])
    for kw in ['news', 'blog', 'wp-json', 'ghost', 'posts', 'articles', 'contentful', 'sanity', 'strapi']:
        for m in list(re.finditer(kw, js))[:6]:
            print(kw, '::', js[max(0, m.start() - 120):m.start() + 120].replace('\n', ' '))
# chunk names
for c in re.findall(r'"static/js/"\+[^;]{0,400}', ''.join(get('https://earth2.io' + s) if not s.startswith('http') else '' for s in srcs))[:2]:
    print('chunkmap', c[:400])
