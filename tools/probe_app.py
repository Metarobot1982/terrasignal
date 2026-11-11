"""One-off: try the public endpoints for territory releases, essence sales and skins; find the banner source."""
import re, urllib.request, urllib.error, json
UA = {'User-Agent': 'Mozilla/5.0 TERRASIGNAL-probe', 'Accept': 'application/json', 'Origin': 'https://app.earth2.io', 'Referer': 'https://app.earth2.io/'}
js = urllib.request.urlopen(urllib.request.Request('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js', headers=UA), timeout=40).read().decode('utf-8', 'replace')
for k in ['BannerSettings', 'bannerText', 'territory_releases', 'territory_essence_sales', '"/skins"', 'skinSaleEndsAt', 'territory_release_winners']:
    for m in list(re.finditer(re.escape(k), js))[:3]:
        print('[%s]' % k, js[max(0, m.start()-300):m.end()+300].replace('\n', ' '))
for base in ['https://r.earth2.io', 'https://app.earth2.io']:
    for path in ['/territory_releases', '/territory_releases/', '/territory_release_winners', '/territory_essence_sales', '/skins', '/banner_settings', '/api/v2/banner_settings/']:
        u = base + path
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30)
            b = r.read().decode('utf-8', 'replace')
            print('OK', u, r.status, r.headers.get('Content-Type'), len(b)); print('   ', b[:900].replace('\n', ' '))
        except urllib.error.HTTPError as e:
            print('ERR', u, e.code, e.read()[:200])
        except Exception as e:
            print('EXC', u, e)
