"""One-off: confirm the land tile zoom constant module."""
import re, urllib.request
js = urllib.request.urlopen(urllib.request.Request('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js', headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read().decode('utf-8', 'replace')
for m in re.finditer(r'r\.d\(t,"h",\(function\(\)\{return L\}\)\)', js):
    start = js.rfind('function(e,t,r){"use strict";', 0, m.start())
    mod = js[start:start + 20000]
    print('HEAD', mod[:1400])
    j = re.search(r'[,\s;(]L=21', mod)
    print('DEF', mod[max(0, j.start() - 700):j.start() + 500] if j else None)
    k = mod.find('bbox'); print('BBOX', mod[max(0, k - 200):k + 200] if k >= 0 else None)
# how getXYFromCoordinates works
i = js.find('getXYFromCoordinates",value'); print('XY', js[i:i + 500])
