#!/usr/bin/env python3
"""Build data/archive.json (every official earth2.io article, Korean title + one line)
and add rule-picked milestones to data/chronicle.json.

Sources: data/inbox/earth2-news-archive.json + data/inbox/earth2-news.json (official text),
tools/backfill/archive-ko.json (Korean, written from that text and checked against it).

Milestone rule (no case-by-case taste): a first launch / official go-live of a system,
a Chapter or Reality Thread, an anniversary, or an official cumulative record.
"""
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def save(p, o):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write('\n')


# id -> short label for the chronicle card
MILESTONES = {
    55: '쥬얼', 104: '멘타·에센스', 146: 'EPL', 377: 'Web3 초안', 534: '자원 히트맵',
    595: '타일 1억', 630: 'E2PRV', 795: '2주년', 937: '레이딩', 982: '레드 에너지',
    791: '시민', 1328: '사이드로이드 거래', 1664: '3주년', 1865: '자원 완성',
    1966: 'GDC 2024', 2125: '런처', 2197: '채굴', 2309: '캐릭터 합성',
    2342: '스테이킹 기록', 2399: '할인 스피너', 3207: '1.1억 스테이킹',
}


def main():
    ko = load(P('tools', 'backfill', 'archive-ko.json'))
    posts = load(P('data', 'inbox', 'earth2-news-archive.json'))['posts'] + load(P('data', 'inbox', 'earth2-news.json'))['items']
    seen, items = set(), []
    for p in posts:
        if p['id'] in seen:
            continue
        seen.add(p['id'])
        layer, title, line = ko[str(p['id'])]
        items.append({'id': p['id'], 'date': p['date'], 'layer': layer, 'titleKo': title, 'line': line,
                      'titleEn': p['title'], 'url': p['url']})
    items.sort(key=lambda x: (x['date'], x['id']), reverse=True)
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    save(P('data', 'archive.json'), {
        'updatedAt': now,
        'note': '어스2 공식 기사(earth2.io/news) 전체. 한국어 제목과 요약은 원문 첫 부분 기준 AI 요약이며, 정확한 내용은 원문이 기준이에요.',
        'items': items})
    print('archive', len(items))

    chron = load(P('data', 'chronicle.json'))
    ev = chron['events']
    have = {e.get('url', '').rstrip('/').split('/')[-1] for e in ev} | {e.get('key') for e in ev}
    by_id = {x['id']: x for x in items}
    added = 0
    for pid, short in MILESTONES.items():
        x = by_id[pid]
        slug = x['url'].rstrip('/').split('/')[-1]
        if slug in have or ('earth2:%d' % pid) in have:
            continue
        ev.append({'layer': x['layer'], 'date': x['date'], 'grade': 'CLEAR', 'short': short,
                   'title': x['titleKo'], 'desc': x['line'], 'source': 'earth2.io 공식 기사 · ' + x['titleEn'],
                   'url': x['url'], 'key': 'earth2:%d' % pid})
        added += 1
    chron['updatedAt'] = now
    save(P('data', 'chronicle.json'), chron)
    print('chronicle +', added, '=', len(ev))


if __name__ == '__main__':
    main()
