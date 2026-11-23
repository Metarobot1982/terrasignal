"""One-off: the new URL-restricted token works from the site and is refused elsewhere."""
import re, urllib.request, urllib.error
tok = re.search(r"TS_MAPBOX = '([^']+)'", open('dive.html', encoding='utf-8').read()).group(1)
u = 'https://api.mapbox.com/v4/mapbox.satellite/16/55898/25381.webp?access_token=' + tok
for ref in ['https://metarobot1982.github.io/terrasignal/dive.html', 'https://example.com/']:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': ref}), timeout=30)
        print('OK', ref, r.status, len(r.read()))
    except urllib.error.HTTPError as e:
        print('ERR', ref, e.code, e.read()[:150])
