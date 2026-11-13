"""One-off: read Earth 2's terms for clauses on bots / automated access / multiple accounts."""
import json, re, html, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 TERRASIGNAL-probe'}
d = json.load(urllib.request.urlopen(urllib.request.Request('https://public-api.wordpress.com/rest/v1.1/sites/195754016/posts?type=page&number=100&fields=ID,title,slug,URL', headers=UA), timeout=40))
for p in d.get('posts', []):
    print('PAGE', p['ID'], p['slug'], '|', p['title'])
for p in d.get('posts', []):
    if re.search(r'term|condition|policy|rules|conduct', p['slug'] + p['title'], re.I):
        c = json.load(urllib.request.urlopen(urllib.request.Request('https://public-api.wordpress.com/rest/v1.1/sites/195754016/posts/%d?fields=content,modified' % p['ID'], headers=UA), timeout=40))
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c['content'])))
        print('==== %s (modified %s) len %d' % (p['slug'], c.get('modified'), len(t)))
        for m in re.finditer(r'[^.]{0,300}\b(bot|bots|automat\w*|script\w*|scrap\w*|crawl\w*|spider|multiple accounts|more than one account|data mining|robot)\b[^.]{0,300}\.', t, re.I):
            print('  >>', m.group(0).strip()[:700])
