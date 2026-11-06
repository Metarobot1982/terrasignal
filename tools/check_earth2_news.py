#!/usr/bin/env python3
"""TERRASIGNAL — check of the official Earth 2 news (earth2.io/news).

earth2.io/news is an app page whose articles come from the official WordPress.com site
(public read API). New articles are recorded in data/inbox/earth2-news.json with status
"pending" and announced as GitHub issues. Nothing is published to the site from here:
publishing happens only after approval (Discord ✅, later step).

The first run stores the whole archive in data/inbox/earth2-news-archive.json (used to
fill the chronicle's past dates) and opens one summary issue instead of one per article.
"""
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

API = 'https://public-api.wordpress.com/rest/v1.1/sites/195754016/posts'
ARTICLE = 'https://earth2.io/news/'
UA = 'TERRASIGNAL-news-check/1.0 (+https://metarobot1982.github.io/terrasignal/)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN = os.path.join(ROOT, 'data', 'inbox', 'earth2-news-seen.json')
INBOX = os.path.join(ROOT, 'data', 'inbox', 'earth2-news.json')
ARCHIVE = os.path.join(ROOT, 'data', 'inbox', 'earth2-news-archive.json')
FIELDS = 'ID,date,modified,title,slug,excerpt,categories,tags'


def get_json(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + '?' + q, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def text(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def kst_date(iso):
    """Official posts carry Sydney time; TERRASIGNAL dates are Korean time."""
    try:
        return datetime.fromisoformat(iso).astimezone(KST).strftime('%Y-%m-%d')
    except (TypeError, ValueError):
        return (iso or '')[:10]


def item(p):
    return {
        'id': p['ID'],
        'date': kst_date(p.get('date')),
        'publishedAt': p.get('date', ''),
        'title': text(p.get('title')),
        'url': ARTICLE + p.get('slug', ''),
        'summary': text(p.get('excerpt'))[:500],
        'categories': sorted((p.get('categories') or {}).keys()),
        'tags': sorted((p.get('tags') or {}).keys()),
    }


def fetch(all_pages):
    out, page = [], 1
    while True:
        d = get_json(API, {'number': 100, 'page': page, 'order_by': 'date', 'order': 'DESC', 'fields': FIELDS})
        posts = d.get('posts', [])
        out += [item(p) for p in posts]
        print('page %d: %d posts (found %s)' % (page, len(posts), d.get('found')))
        if not all_pages or len(posts) < 100 or page >= 20:
            return out
        page += 1


def gh_issue(title, body):
    token, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo:
        print('[issue skipped — no token]', title)
        return
    data = json.dumps({'title': title, 'body': body[:60000]}).encode()
    req = urllib.request.Request('https://api.github.com/repos/%s/issues' % repo, data=data, method='POST',
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print('issue', r.status, title)
    except urllib.error.HTTPError as e:
        print('issue failed', e.code, e.read()[:300])


def main():
    seen = load(SEEN, None)
    first = seen is None
    posts = fetch(all_pages=first)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if first:
        save(ARCHIVE, {'source': API, 'savedAt': now, 'posts': posts})
        rows = '\n'.join('| %s | %s |' % (p['date'], '[%s](%s)' % (p['title'].replace('|', '/'), p['url'])) for p in posts)
        gh_issue('📡 earth2.io 공식 뉴스 첫 수집 — 기사 %d개' % len(posts),
                 '첫 실행이라 지금까지의 공식 기사를 모두 기록했어요 (`data/inbox/earth2-news-archive.json`). '
                 '이 목록으로 개척 연대기의 과거 날짜를 확인해요. 다음 실행부터는 새 기사만 알려드려요.\n\n| 날짜 | 기사 |\n|---|---|\n' + rows)
        seen = {'ids': []}
    else:
        inbox = load(INBOX, {'items': []})
        known = set(seen.get('ids', []))
        new = [p for p in posts if p['id'] not in known]
        print('new articles: %d' % len(new))
        for p in reversed(new):
            inbox['items'].append(dict(p, source='earth2.io', status='pending', receivedAt=now))
            gh_issue('📡 새 공식 신호: %s' % p['title'],
                     '**날짜** %s\n**원문** %s\n\n> %s\n\n상태: 승인 대기 — 사이트에는 아직 반영되지 않았어요.' % (p['date'], p['url'], p['summary']))
        save(INBOX, inbox)
    seen['ids'] = sorted(set(seen.get('ids', [])) | {p['id'] for p in posts})
    seen['checkedAt'] = now
    save(SEEN, seen)


if __name__ == '__main__':
    main()
