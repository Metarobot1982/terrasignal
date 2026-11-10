"""One-off (v3) check that the Claude API key works and the decoding reads well (prints only)."""
import json
import urllib.request

import ai_decode

API = 'https://public-api.wordpress.com/rest/v1.1/sites/195754016/posts?number=2&fields=ID,title,date'
req = urllib.request.Request(API, headers={'User-Agent': 'TERRASIGNAL-news-check/1.0'})
posts = json.load(urllib.request.urlopen(req, timeout=30))['posts']
for p in posts:
    body = ai_decode.article_text(p['ID'])
    print('====', p['date'], p['title'], '(%d chars)' % len(body))
    print(json.dumps(ai_decode.decode(p['title'], body, 'earth2.io 공식 기사'), ensure_ascii=False, indent=1))
print('banner:', ai_decode.banner_ko('MENTAR STAKER DISCOUNT PERK'))
