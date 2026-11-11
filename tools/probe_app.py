"""One-off: (1) how app.earth2.io defines a tile (quadkey zoom / size), (2) why Mapbox tiles answer 429."""
import re, urllib.request, urllib.error
UA = {'User-Agent': 'Mozilla/5.0 TERRASIGNAL-probe'}
def get(u, h=None):
    return urllib.request.urlopen(urllib.request.Request(u, headers=dict(UA, **(h or {}))), timeout=40).read().decode('utf-8', 'replace')
js = get('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js')
pats = [r'[Qq]uad[Kk]ey\w*\s*[:=(][^;]{0,160}', r'(?:tile|TILE)\w*(?:Zoom|ZOOM|Level|LEVEL|Size|SIZE)\w*\s*[:=]\s*[\d.]+', r'tileToQuadkey|quadkeyToTile|tileXYToQuadKey|getQuadkey\w*',
        r'(?:sqm|square met|m²|metres|meters)[^"\']{0,80}', r'\b(?:21|22|23)\b\s*[,)][^;]{0,40}quad', r'quadkey[^;]{0,60}length']
for p in pats:
    for m in list(re.finditer(p, js))[:8]:
        a = max(0, m.start() - 200)
        print('[%s]' % p, js[a:m.end() + 200].replace('\n', ' '))
print('=== mapbox')
tok = re.search(r"TS_MAPBOX = '([^']+)'", open('dive.html', encoding='utf-8').read()).group(1)
for u in ['https://api.mapbox.com/styles/v1/mapbox/satellite-v9?access_token=' + tok,
          'https://api.mapbox.com/v4/mapbox.satellite/3/7/3.webp?access_token=' + tok,
          'https://api.mapbox.com/v4/mapbox.satellite/15/29000/16300.webp?access_token=' + tok]:
    for ref in [None, 'https://metarobot1982.github.io/terrasignal/dive.html']:
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=dict(UA, **({'Referer': ref} if ref else {}))), timeout=30)
            print(u.split('?')[0], ref, r.status, r.headers.get('Content-Type'), len(r.read()))
        except urllib.error.HTTPError as e:
            print(u.split('?')[0], ref, e.code, e.read()[:300])
