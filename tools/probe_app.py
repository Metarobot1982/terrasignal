"""One-off: find and read Earth 2's Terms & Conditions for automated-access clauses."""
import re, html, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0'}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode('utf-8', 'replace')
js = get('https://frontend.earth2.io/static/js/main.4ea4359c.chunk.js')
urls = sorted(set(re.findall(r'https?://[^"\'\s)]*(?:terms|tos|conditions|legal)[^"\'\s)]*', js, re.I)))
print('URLS', urls)
for u in urls:
    try:
        if 'docs.google.com/document' in u:
            m = re.search(r'/d/([\w-]+)', u); u = 'https://docs.google.com/document/d/%s/export?format=txt' % m.group(1)
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', get(u))))
        print('==== %s len %d' % (u, len(t))); print('  head:', t[:300])
        for m in re.finditer(r'[^.]{0,300}\b(bot|bots|automat\w*|script\w*|scrap\w*|crawl\w*|spider|multiple accounts|more than one account|data mining|robot\w*)\b[^.]{0,300}\.', t, re.I):
            print('  >>', m.group(0).strip()[:800])
    except Exception as e:
        print('fail', u, e)
