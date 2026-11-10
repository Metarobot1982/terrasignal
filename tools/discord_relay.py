#!/usr/bin/env python3
"""TERRASIGNAL — Discord relay and approval.

1. Reads new messages in the Relay Station announcement channels (official Earth 2
   announcements followed into the server) and new earth2.io articles waiting in
   data/inbox/earth2-news.json.
2. Posts each one as a draft in the private approval channel, with ✅ ❌ 📜 reactions.
3. Reads the operator's reactions and replies on open drafts:
   ✅  publish to the site (data/map.json → 전역 송출)
   📜  also record it in the chronicle (data/chronicle.json)
   ❌  discard
   A reply to a draft becomes the Korean description shown on the site.
   #현실 / #경계 / #디지털 in the reply changes the layer.

Runs inside GitHub Actions. Needs the secret DISCORD_BOT_TOKEN. Uses only the
standard library. Nothing reaches the site without ✅.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = 'https://discord.com/api/v10'
UA = 'DiscordBot (https://metarobot1982.github.io/terrasignal/, 1.0)'
KST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, 'data', 'inbox', 'discord-config.json')
STATE = os.path.join(ROOT, 'data', 'inbox', 'discord-state.json')
DRAFTS = os.path.join(ROOT, 'data', 'inbox', 'discord-drafts.json')
NEWS = os.path.join(ROOT, 'data', 'inbox', 'earth2-news.json')
MAP = os.path.join(ROOT, 'data', 'map.json')
CHRON = os.path.join(ROOT, 'data', 'chronicle.json')

OK, NO, BOOK = '✅', '❌', '📜'
LAYER_NAME = {'real': '■ 현실 지구', 'border': '◆ 경계', 'digital': '⬢ 디지털 지구'}
LAYER_TAG = {'#현실': 'real', '#경계': 'border', '#디지털': 'digital'}
CHRON_LAYER = {'real': 'R', 'border': 'B', 'digital': 'D'}
MAX_GLOBALS = 12

# Keyword guess for the layer; the operator can correct it with #현실 / #경계 / #디지털.
RULES = [
    ('digital', r'reality thread|e2v1|pre-?alpha|crafting|quest|hordes?|combat|teleport|farming|cooking|recipe|avatar|emote|chapter \d'),
    ('real', r'territor|tier ?3|\bt3\b|\bt2\b|\bt1\b|tiles?\b|land\b|propert|countr|megacit|epl\b|referral'),
    ('border', r'skin|essence|\$?ess\b|staking|staker|mentar|jewel|cydroid|droid|raid|bazaar|civilian|withdraw|e-?ther'),
]


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


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


class Discord:
    def __init__(self, token):
        self.token = token

    def call(self, method, path, body=None, query=None):
        url = API + path + ('?' + urllib.parse.urlencode(query) if query else '')
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, method=method, headers={
                'Authorization': 'Bot ' + self.token, 'User-Agent': UA, 'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    time.sleep(0.4)
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = float(json.loads(e.read() or b'{}').get('retry_after', 2))
                    time.sleep(min(wait + 0.5, 30))
                    continue
                detail = e.read()[:300].decode('utf-8', 'replace')
                raise RuntimeError('%s %s → %s %s' % (method, path, e.code, detail))
        raise RuntimeError('%s %s → rate limited' % (method, path))

    def messages(self, channel, after=None, limit=50):
        q = {'limit': limit}
        if after:
            q['after'] = after
        msgs = self.call('GET', '/channels/%s/messages' % channel, query=q) or []
        return sorted(msgs, key=lambda m: int(m['id']))

    def post(self, channel, content, embed=None):
        body = {'content': content, 'allowed_mentions': {'parse': []}}
        if embed:
            body['embeds'] = [embed]
        return self.call('POST', '/channels/%s/messages' % channel, body)

    def edit(self, channel, mid, content):
        return self.call('PATCH', '/channels/%s/messages/%s' % (channel, mid), {'content': content})

    def react(self, channel, mid, emoji):
        self.call('PUT', '/channels/%s/messages/%s/reactions/%s/@me' % (channel, mid, urllib.parse.quote(emoji)))

    def reactors(self, channel, mid, emoji):
        try:
            return self.call('GET', '/channels/%s/messages/%s/reactions/%s' % (channel, mid, urllib.parse.quote(emoji))) or []
        except RuntimeError:
            return []


def clean(s):
    s = re.sub(r'<a?:\w+:\d+>', '', s or '')            # custom emoji
    s = re.sub(r'<[@#&!]+\d+>', '', s)                  # mentions
    s = re.sub(r'[*_~`>|]{1,3}', '', s)                 # markdown marks
    return re.sub(r'[ \t]+', ' ', s).strip()


def message_text(m):
    parts = [m.get('content') or '']
    for e in m.get('embeds') or []:
        parts += [e.get('title') or '', e.get('description') or '']
    return clean('\n'.join(p for p in parts if p))


def first_link(m):
    text = (m.get('content') or '') + ' ' + ' '.join((e.get('url') or '') + ' ' + (e.get('description') or '') for e in m.get('embeds') or [])
    links = re.findall(r'https?://[^\s)>\]]+', text)
    for l in links:
        if 'earth2.io' in l:
            return l
    return links[0] if links else ''


def guess_layer(text):
    t = text.lower()
    for layer, pat in RULES:
        if re.search(pat, t):
            return layer
    return 'border'


def kst_date(iso):
    try:
        return datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(KST).strftime('%Y-%m-%d')
    except (AttributeError, ValueError):
        return datetime.now(KST).strftime('%Y-%m-%d')


def draft_embed(d):
    return {
        'title': ('📡 ' + d['title'])[:250],
        'url': d['url'] or None,
        'description': d['excerpt'][:1500] or '(본문 없음)',
        'color': {'real': 0x2FE6C8, 'border': 0xFF2FB0, 'digital': 0x7D6BFF}[d['layer']],
        'fields': [
            {'name': '층 추정', 'value': LAYER_NAME[d['layer']], 'inline': True},
            {'name': '등급', 'value': d['grade'], 'inline': True},
            {'name': '날짜 (한국 시간)', 'value': d['date'], 'inline': True},
            {'name': '출처', 'value': d['sourceLabel'][:200], 'inline': False},
        ],
        'footer': {'text': '✅ 사이트 반영 · ❌ 버리기 · 📜 연대기에도 기록 · 답장하면 그 글이 사이트 설명이 돼요 (#현실 #경계 #디지털 로 층 변경)'},
    }


def new_draft(dc, cfg, drafts, src):
    msg = dc.post(cfg['approvalChannel'], '🟡 **승인 대기** — 새 신호가 들어왔어요.', draft_embed(src))
    for e in (OK, NO, BOOK):
        dc.react(cfg['approvalChannel'], msg['id'], e)
    src.update({'draftId': msg['id'], 'status': 'pending', 'createdAt': now_iso()})
    drafts['items'].append(src)
    print('draft', msg['id'], src['title'][:60])


def collect(dc, cfg, state, drafts):
    """Post drafts for new announcements and new earth2.io articles."""
    first_run = not state.get('lastSeen')
    state.setdefault('lastSeen', {})
    init = {}
    for ch in cfg['sourceChannels']:
        if first_run or ch['id'] not in state['lastSeen']:
            latest = dc.messages(ch['id'], limit=1)
            init[ch['id']] = latest[-1]['id'] if latest else '0'
            if first_run and latest and ch is cfg['sourceChannels'][0] and latest[-1].get('type', 0) in (0, 19):
                new_draft(dc, cfg, drafts, source_from_message(latest[-1], ch, test=True))
    state['lastSeen'].update(init)  # only after the test draft was posted successfully
    for ch in cfg['sourceChannels']:
        cid = ch['id']
        if cid in init:
            continue
        for m in dc.messages(cid, after=state['lastSeen'][cid]):
            state['lastSeen'][cid] = m['id']
            if m.get('type', 0) not in (0, 19) or not message_text(m):
                continue  # skip system notices such as "channel followed"
            new_draft(dc, cfg, drafts, source_from_message(m, ch))
    news = load(NEWS, {'items': []})
    for it in news['items']:
        if it.get('status') == 'pending' and not it.get('draftId'):
            src = {
                'kind': 'earth2.io', 'title': it['title'], 'excerpt': it.get('summary', ''), 'url': it['url'],
                'date': it.get('date') or datetime.now(KST).strftime('%Y-%m-%d'), 'grade': 'CLEAR',
                'layer': guess_layer(it['title'] + ' ' + it.get('summary', '')),
                'sourceLabel': 'earth2.io 공식 기사', 'sourceKey': 'earth2:%s' % it.get('id'),
            }
            new_draft(dc, cfg, drafts, src)
            it['draftId'] = src['draftId']
            it['status'] = 'drafted'
    save(NEWS, news)
    if first_run:
        dc.post(cfg['approvalChannel'], '📡 **TERRASIGNAL 봇 연결 완료.** 공지 채널 %d개를 지켜보고 있어요. '
                '위 초안은 연결 시험용으로 가장 최근 공지를 가져온 거예요. ✅를 누르면 사이트에 실제로 올라가고, ❌를 누르면 버려져요.'
                % len(cfg['sourceChannels']))


def source_from_message(m, ch, test=False):
    text = message_text(m)
    lines = [l for l in text.splitlines() if l.strip()]
    title = lines[0][:140] if lines else '(제목 없음)'
    return {
        'kind': 'discord', 'title': title, 'excerpt': '\n'.join(lines[1:])[:1500] if len(lines) > 1 else '',
        'url': first_link(m), 'date': kst_date(m.get('timestamp')), 'grade': 'CLEAR',
        'layer': guess_layer(text), 'sourceLabel': '어스2 공식 디스코드 · #%s%s' % (ch['name'], ' (연결 시험)' if test else ''),
        'sourceKey': 'discord:%s:%s' % (ch['id'], m['id']),
    }


def operator_replies(dc, cfg, drafts, bot_id):
    """Map draft id → latest operator reply text."""
    open_ids = {d['draftId'] for d in drafts['items'] if d['status'] == 'pending'}
    if not open_ids:
        return {}
    oldest = min(open_ids, key=int)
    out, after = {}, str(int(oldest) - 1)
    for _ in range(10):
        batch = dc.messages(cfg['approvalChannel'], after=after, limit=100)
        if not batch:
            break
        for m in batch:
            ref = (m.get('message_reference') or {}).get('message_id')
            if ref in open_ids and m['author']['id'] != bot_id and (m.get('content') or '').strip():
                out[ref] = m['content'].strip()
        after = batch[-1]['id']
        if len(batch) < 100:
            break
    return out


def apply_reply(d, reply):
    for tag, layer in LAYER_TAG.items():
        if tag in reply:
            d['layer'] = layer
            reply = reply.replace(tag, '')
    reply = clean(reply)
    if reply:
        d['descKo'] = reply


def publish(d, to_chronicle):
    m = load(MAP, None)
    if m is None:
        raise RuntimeError('data/map.json missing')
    if d['kind'] == 'countdown':
        cds = [c for c in m.get('countdowns', []) if c.get('key')]  # real entries replace the placeholders
        cds = [c for c in cds if c['key'] != d['sourceKey']]
        cd = dict(d['countdown'], key=d['sourceKey'])
        if d.get('descKo'):
            cd['note'] = d['descKo']  # operator's reply becomes the Korean line on the card
        cds.append(cd)
        m['countdowns'] = cds
        m['updatedAt'] = now_iso()
        save(MAP, m)
        return
    y, mo, da = d['date'].split('-')
    entry = {'L': d['layer'], 'g': d['grade'], 'title': d['title'], 'desc': d.get('descKo') or d['excerpt'][:160] or d['title'],
             'date': '%s.%s.%s · %s' % (y, mo, da, '공식 기사' if d['kind'] == 'earth2.io' else '공식 디스코드'),
             'url': d['url'], 'key': d['sourceKey']}
    m['globals'] = [g for g in m.get('globals', []) if g.get('key') != d['sourceKey']]
    m['globals'].insert(0, entry)
    m['globals'] = m['globals'][:MAX_GLOBALS]
    m['updatedAt'] = now_iso()
    save(MAP, m)
    if to_chronicle:
        c = load(CHRON, {'events': []})
        if not any(e.get('key') == d['sourceKey'] for e in c['events']):
            c['events'].append({'layer': CHRON_LAYER[d['layer']], 'date': d['date'], 'grade': d['grade'],
                                'short': d['title'][:14], 'title': d['title'], 'desc': entry['desc'],
                                'source': ('earth2.io 공식 기사' if d['kind'] == 'earth2.io' else '어스2 공식 디스코드'),
                                'url': d['url'], 'key': d['sourceKey']})
            c['updatedAt'] = now_iso()
            save(CHRON, c)


def review(dc, cfg, drafts, bot_id):
    replies = operator_replies(dc, cfg, drafts, bot_id)
    changed = False
    for d in drafts['items']:
        if d['status'] != 'pending':
            continue
        if d['draftId'] in replies:
            apply_reply(d, replies[d['draftId']])
        voters = {}
        for e in (OK, NO, BOOK):
            voters[e] = [u for u in dc.reactors(cfg['approvalChannel'], d['draftId'], e) if u['id'] != bot_id and not u.get('bot')]
        if voters[NO]:
            d['status'], d['decidedAt'] = 'rejected', now_iso()
            dc.edit(cfg['approvalChannel'], d['draftId'], '⚪ **버림** — 사이트에 반영하지 않았어요.')
            changed = True
        elif voters[OK]:
            chron = bool(voters[BOOK])
            publish(d, chron)
            d['status'], d['decidedAt'], d['chronicle'] = 'published', now_iso(), chron
            if d['kind'] == 'countdown':
                dc.edit(cfg['approvalChannel'], d['draftId'], '🟢 **반영됨** — 곧 열리는 시그널에 올라가요. 이후 어사이드가 보내는 남은 시간은 자동으로 갱신돼요.')
                print('published countdown', d['title'][:60])
                continue
            dc.edit(cfg['approvalChannel'], d['draftId'],
                    '🟢 **반영됨** — 1~3분 뒤 사이트 시그널 지도에 올라가요.%s%s' % (
                        ' 개척 연대기에도 기록했어요.' if chron else '',
                        ' (설명: 대표님 답장)' if d.get('descKo') else ' (설명: 원문 발췌 — 답장으로 한국어 설명을 넣을 수 있어요)'))
            changed = True
            print('published', d['title'][:60], 'chronicle' if chron else '')
    return changed


# ---------------------------------------------------------------- Aside reports
# The Aside browser routine (operator's PC, logged in to app.earth2.io) posts a
# report in the Aside channel. Each line:  종류 | 제목 | 장소 | 남은 시간 | 단계
#   종류: 영토 · 스킨 · 스테이커 · 에센스타일 · 기타
#   남은 시간: "2일 14시간 36분", "14시간 5분", "2D 14:36:20", "14:36:20"
#   단계(영토만): 투표 · 결과 · 카운트다운 · 오픈
KIND = {
    '영토': ('real', 'vote'), '스킨': ('border', 'ops'), '스테이커': ('border', ''),
    '에센스타일': ('real', ''), '기타': ('border', ''),
}
STAGE = {'투표': 1, '결과': 2, '카운트다운': 3, '오픈': 4}


def parse_left(t):
    t = t.strip().upper().replace(' ', '')
    m = re.match(r'^(?:(\d+)(?:일|D))?(?:(\d+)(?:시간|H))?(?:(\d+)(?:분|M))?(?:(\d+)(?:초|S))?$', t)
    if m and any(m.groups()):
        d, h, mi, se = (int(x or 0) for x in m.groups())
        return d * 86400 + h * 3600 + mi * 60 + se
    m = re.match(r'^(\d+):(\d{1,2}):(\d{2}):(\d{2})$', t)  # 일:시:분:초 (배너 표기)
    if m:
        d, h, mi, se = (int(x) for x in m.groups())
        return d * 86400 + h * 3600 + mi * 60 + se
    m = re.match(r'^(?:(\d+)(?:일|D))?(\d{1,2}):(\d{2})(?::(\d{2}))?$', t)
    if m:
        d, h, mi, se = (int(x or 0) for x in m.groups())
        return d * 86400 + h * 3600 + mi * 60 + se
    return None


def parse_report(m):
    """Return countdown dicts from one Aside message (lines after [TS-AUTO])."""
    text = m.get('content') or ''
    if '[TS-AUTO]' not in text:
        return []
    sent = datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00'))
    out = []
    for line in text.split('[TS-AUTO]', 1)[1].splitlines():
        cols = [c.strip() for c in line.strip().strip('-•').split('|')]
        if len(cols) < 4 or cols[0] not in KIND:
            continue
        kind, title, place, left = cols[:4]
        stage = STAGE.get(cols[4], 0) if len(cols) > 4 else 0
        secs = parse_left(left)
        layer, cycle = KIND[kind]
        ends = (sent + timedelta(seconds=secs)).strftime('%Y-%m-%dT%H:%M:%SZ') if secs is not None else ''
        out.append({'L': layer, 'place': place or '전역', 'cycle': cycle, 'stage': stage if kind == '영토' else 0,
                    'title': title, 'endsAt': ends,
                    'note': '플레이어 투표로 열리는 영토. 열리면 T3 땅이 해금돼요.' if kind == '영토' else ''})
    return out


def aside(dc, cfg, state, drafts):
    ch = cfg.get('asideChannel')
    if not ch:
        return
    after = state.get('asideLastSeen')
    if not after:
        latest = dc.messages(ch, limit=1)
        state['asideLastSeen'] = latest[-1]['id'] if latest else '0'
        after = state['asideLastSeen']
    reports = []
    for m in dc.messages(ch, after=after, limit=100):
        state['asideLastSeen'] = m['id']
        reports += parse_report(m)
    if not reports:
        return
    mp = load(MAP, {})
    live = {c.get('key'): c for c in mp.get('countdowns', []) if c.get('key')}
    pending = {d['sourceKey'] for d in drafts['items'] if d['status'] == 'pending'}
    rejected = {d['sourceKey'] for d in drafts['items'] if d['status'] == 'rejected'}
    updated = False
    for c in reports:
        key = 'countdown:%s:%s' % (c['title'], c['place'])
        if key in live:  # approved before → keep the time fresh without asking again
            live[key].update({k: c[k] for k in ('endsAt', 'stage') if c[k] or k == 'stage'})
            updated = True
        elif key not in pending and key not in rejected:
            when = c['endsAt'] or '시각 확인 중'
            src = {'kind': 'countdown', 'title': c['title'], 'countdown': c,
                   'excerpt': '장소: %s\n끝나는 시각(UTC): %s%s' % (c['place'], when, '\n단계: %s' % c['stage'] if c['stage'] else ''),
                   'url': '', 'date': datetime.now(KST).strftime('%Y-%m-%d'), 'grade': 'CLEAR', 'layer': c['L'],
                   'sourceLabel': '어사이드 수집 · app.earth2.io (로그인 화면)', 'sourceKey': key}
            new_draft(dc, cfg, drafts, src)
            pending.add(key)
    now = datetime.now(timezone.utc)
    keep = []
    for c in mp.get('countdowns', []):
        try:
            gone = c.get('key') and c.get('endsAt') and now - datetime.fromisoformat(c['endsAt'].replace('Z', '+00:00')) > timedelta(days=1)
        except ValueError:
            gone = False
        if gone:
            updated = True
        else:
            keep.append(c)
    if updated:
        mp['countdowns'] = keep
        mp['updatedAt'] = now_iso()
        save(MAP, mp)


def main():
    token = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
    if not token:
        print('DISCORD_BOT_TOKEN is not set — skipping Discord relay.')
        return
    cfg = load(CONFIG, None)
    if not cfg:
        sys.exit('data/inbox/discord-config.json missing')
    dc = Discord(token)
    bot_id = dc.call('GET', '/users/@me')['id']
    state = load(STATE, {})
    drafts = load(DRAFTS, {'items': []})
    try:
        review(dc, cfg, drafts, bot_id)
        collect(dc, cfg, state, drafts)
        aside(dc, cfg, state, drafts)
    finally:
        state['checkedAt'] = now_iso()
        save(STATE, state)
        save(DRAFTS, drafts)


if __name__ == '__main__':
    main()
