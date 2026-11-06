#!/usr/bin/env python3
"""TERRASIGNAL — daily check of the official Earth 2 news (earth2.io).

Finds article links, compares them with data/inbox/earth2-news-seen.json and, for each
new article, records it in data/inbox/earth2-news.json (status "pending") and opens a
GitHub issue so the operator is notified. Nothing is published to the site from here:
publishing happens only after approval (Discord ✅, later step).

The first run only records what already exists (no issue per article) and opens one
summary issue listing the archive, which is used to fill the chronicle's past dates.
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE = 'https://earth2.io'
LIST_URLS = [BASE + '/sitemap.xml', BASE + '/news', BASE + '/news/']
UA = 'Mozilla/5.0 (compatible; TERRASIGNAL-news-check/1.0; +https://metarobot1982.github.io/terrasignal/)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN = os.path.join(ROOT, 'data', 'inbox', 'earth2-news-seen.json')
INBOX = os.path.join(ROOT, 'data', 'inbox', 'earth2-news.json')
ART = re.compile(r'https?://(?:www\.)?earth2\.io/news/[a-z0-9][a-z0-9\-_/]*[a-z0-9]', re.I)
REL = re.compile(r'href="(/news/[a-z0-9][a-z0-9\-_/]*[a-z0-9])"', re.I)
MAX_FETCH = 40


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xml;q=0.9,*/*;q=0.8'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


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


def collect_links():
    links, notes = set(), []
    for url in LIST_URLS:
        try:
            body = get(url)
        except Exception as e:  # noqa: BLE001
            notes.append('%s → %s' % (url, e))
            continue
        if os.environ.get('NEWS_DEBUG'):
            print('--- %s : %d bytes' % (url, len(body)))
            print('title:', (re.search(r'<title>([^<]*)', body) or [None, ''])[1][:120])
            print('"/news" occurrences:', body.count('/news'))
            print('hrefs:', sorted(set(re.findall(r'href="([^"#]+)"', body)))[:60])
            print('locs:', re.findall(r'<loc>([^<]+)</loc>', body)[:40])
            i = body.find('/news/')
            print('context:', body[max(0, i - 200):i + 300] if i >= 0 else '-')
        found = set(m.rstrip('/') for m in ART.findall(body))
        found |= set(BASE + m.rstrip('/') for m in REL.findall(body))
        # sitemap index → follow child sitemaps that look like posts/news
        if url.endswith('.xml'):
            for sm in re.findall(r'<loc>([^<]+\.xml)</loc>', body):
                if re.search(r'post|news|article', sm, re.I):
                    try:
                        sub = get(sm)
                        found |= set(m.rstrip('/') for m in ART.findall(sub))
                    except Exception as e:  # noqa: BLE001
                        notes.append('%s → %s' % (sm, e))
        notes.append('%s → %d links' % (url, len(found)))
        links |= found
    links = {l for l in links if l.rstrip('/') != BASE + '/news'}
    return sorted(links), notes


def meta(body, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]+)"' % re.escape(n), body, re.I) \
            or re.search(r'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="%s"' % re.escape(n), body, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ''


def article_info(url):
    info = {'url': url, 'title': '', 'date': '', 'summary': ''}
    try:
        body = get(url)
    except Exception as e:  # noqa: BLE001
        info['error'] = str(e)
        return info
    info['title'] = meta(body, 'og:title', 'twitter:title')
    if not info['title']:
        m = re.search(r'<title>([^<]+)</title>', body, re.I)
        info['title'] = html.unescape(m.group(1)).strip() if m else ''
    d = meta(body, 'article:published_time', 'og:published_time', 'date')
    if not d:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', body)
        d = m.group(1) if m else ''
    if not d:
        m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (20\d\d)', body)
        if m:
            d = datetime.strptime(' '.join(m.groups()), '%B %d %Y').strftime('%Y-%m-%d')
    info['date'] = d[:10]
    info['summary'] = meta(body, 'og:description', 'description')[:400]
    return info


def gh_issue(title, body):
    token, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo:
        print('[issue skipped — no token]', title)
        return
    data = json.dumps({'title': title, 'body': body, 'labels': ['signal-inbox']}).encode()
    req = urllib.request.Request('https://api.github.com/repos/%s/issues' % repo, data=data, method='POST',
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print('issue', r.status, title)
    except urllib.error.HTTPError as e:
        print('issue failed', e.code, e.read()[:300])


def main():
    links, notes = collect_links()
    print('\n'.join(notes))
    if not links:
        print('No article links found. earth2.io may render the list with scripts or block automated requests.')
        sys.exit(1)
    seen = load(SEEN, None)
    first = seen is None
    seen = seen or {'urls': []}
    inbox = load(INBOX, {'items': []})
    new = [l for l in links if l not in set(seen['urls'])]
    print('found %d, new %d, first run: %s' % (len(links), len(new), first))
    infos = []
    for url in new[:MAX_FETCH]:
        infos.append(article_info(url))
        time.sleep(1)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if first:
        rows = sorted(infos, key=lambda i: i['date'] or '0', reverse=True)
        table = '\n'.join('| %s | %s | %s |' % (i['date'] or '?', (i['title'] or '?').replace('|', '/'), i['url']) for i in rows)
        more = '\n\n그 밖에 %d개 링크는 다음 실행부터 기준으로만 기록했어요.' % (len(new) - len(infos)) if len(new) > len(infos) else ''
        gh_issue('📡 earth2.io 공식 뉴스 첫 수집 — 기사 %d개' % len(links),
                 '첫 실행이라 지금 있는 기사를 기준으로 기록했어요. 이 목록으로 개척 연대기의 과거 날짜를 확인해요.\n\n| 날짜 | 제목 | 주소 |\n|---|---|---|\n' + table + more)
    else:
        for i in infos:
            inbox['items'].append({'source': 'earth2.io', 'status': 'pending', 'receivedAt': now, **i})
            gh_issue('📡 새 공식 신호: %s' % (i['title'] or i['url']),
                     '**날짜** %s\n**주소** %s\n\n%s\n\n상태: 승인 대기 (사이트에는 아직 반영되지 않았어요)' % (i['date'] or '확인 중', i['url'], i['summary']))
    seen['urls'] = sorted(set(seen['urls']) | set(links))
    seen['checkedAt'] = now
    save(SEEN, seen)
    save(INBOX, inbox)


if __name__ == '__main__':
    main()
