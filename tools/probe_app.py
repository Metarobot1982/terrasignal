"""One-off: find the zoom level Earth 2 uses for its land tiles (constant used by getTileLength)."""
import re, urllib.request, math
js = urllib.request.urlopen(urllib.request.Request('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js', headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read().decode('utf-8', 'replace')
i = js.find('getTileLength",value')
print('ctx', js[i-100:i+400])
# module that exports "h" together with "p" (tilebelt-like) and "t","i","f","j"
for m in re.finditer(r'r\.d\(t,"h",\(function\(\)\{return (\w+)\}\)\)', js):
    start = js.rfind('function(e,t,r){"use strict";', 0, m.start())
    mod = js[start:start+60000]
    var = m.group(1)
    a = re.search(r'[,\s;(]' + re.escape(var) + r'=([^,;]{1,40})', mod)
    if a and re.match(r'^\s*[\d.e]+\s*$', a.group(1)):
        print('export h ->', var, '=', a.group(1), '| module head:', mod[:200].replace('\n', ' '))
for m in re.finditer(r'(\w+)=(2[0-4])[,;][^;]{0,80}', js):
    s = js[max(0, m.start()-80):m.end()]
    if re.search(r'zoom|Zoom|ZOOM|tile|Tile', s):
        print('num', s.replace('\n', ' '))
for z in (20, 21, 22, 23):
    eq = 40075016.686 / 2 ** z
    print('z%d equator %.2fm  seoul37.5 %.2fm  (%.1f m2 = %.1f pyeong)' % (z, eq, eq * math.cos(math.radians(37.53)), (eq * math.cos(math.radians(37.53))) ** 2, (eq * math.cos(math.radians(37.53))) ** 2 / 3.3058))
