"""One-off: do Mapbox satellite tiles load for the site's token now?"""
import re, urllib.request, urllib.error
tok = re.search(r"TS_MAPBOX = '([^']+)'", open('dive.html', encoding='utf-8').read()).group(1)
H = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://metarobot1982.github.io/terrasignal/dive.html'}
for u in ['https://api.mapbox.com/styles/v1/mapbox/satellite-v9?access_token=' + tok,
          'https://api.mapbox.com/v4/mapbox.satellite/3/7/3.webp?access_token=' + tok,
          'https://api.mapbox.com/v4/mapbox.satellite/16/55898/25381.webp?access_token=' + tok]:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30)
        print('OK', u.split('?')[0], r.status, r.headers.get('Content-Type'), len(r.read()))
    except urllib.error.HTTPError as e:
        print('ERR', u.split('?')[0], e.code, e.read()[:200])
