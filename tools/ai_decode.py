"""TERRASIGNAL — AI 해독 (Claude API).

Turns an official Earth 2 announcement into a Korean draft: a Korean title, up to three
decoded lines, the layer and whether it belongs in the chronicle. The operator still
checks every draft in Discord and approves with ✅; nothing is published by the AI.

Needs the GitHub secret ANTHROPIC_API_KEY. Without it every function returns None and
the relay keeps working with the English original.
"""
import json
import os
import re
import urllib.error
import urllib.request

API = 'https://api.anthropic.com/v1/messages'
MODEL = os.environ.get('TS_AI_MODEL', 'claude-sonnet-5-5')
WP_POST = 'https://public-api.wordpress.com/rest/v1.1/sites/195754016/posts/%s?fields=content,title'

SYSTEM = """너는 TERRASIGNAL 방송국의 해독 담당이야. TERRASIGNAL은 METAFUNK AGENCY가 운영하는,
Earth 2(어스2) 소식을 한국어로 전하는 비공식 메타버스 방송국이야.

원문(어스2 공식 발표)을 읽고 한국어 해독 초안을 JSON으로만 답해.

규칙
- 원문에 적힌 사실만 쓴다. 추측, 과장, 예측, 원문에 없는 숫자는 절대 넣지 않는다.
- 구매·투자 권유 표현을 쓰지 않는다 ("지금 사세요", "기회" 등 금지). 할인·드롭은 무엇을, 언제, 어디서만.
- 쉬운 존댓말 "~요" 체, 한 줄은 60자 안팎.
- 게임 용어는 공식 영어 이름을 살린다 (예: E2V1, Reality Thread → 리얼리티 스레드, Essence/$ESS → 에센스, Cydroid → 사이드로이드, Mentar → 멘타, Territory → 영토/테리토리).
- "행성"이라는 말은 쓰지 않는다. 세계는 "디지털 지구".
- 층(layer): real = 현실 지구(땅, 영토, 타일, 국가, 프로퍼티), border = 경계(에센스, 스테이킹, 스킨, 사이드로이드, 레이딩, 쥬얼, 바자르, 출금), digital = 디지털 지구(E2V1, 리얼리티 스레드, 제작, 전투, 퀘스트, 호드, 아바타).
- chronicle: 세계 구조가 바뀐 일(새 리얼리티 스레드, 새 시스템 도입, 접근권 확대, 공식 기념일)만 true. 패치·버그 수정·이벤트·할인·카운트다운·시즌 스킨은 false.
- 원문이 너무 짧거나 내용이 불분명하면 lines를 1줄로 하고 "자세한 내용은 공식 원문에서 확인해 주세요."를 넣는다.

출력 형식 (JSON 하나만, 다른 글 없이)
{"titleKo": "한국어 제목", "lines": ["해독 1", "해독 2", "해독 3"], "layer": "real|border|digital", "chronicle": false}"""


def _post(body, key):
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method='POST', headers={
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def article_text(post_id):
    try:
        req = urllib.request.Request(WP_POST % post_id, headers={'User-Agent': 'TERRASIGNAL-news-check/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except (urllib.error.URLError, ValueError):
        return ''
    html = d.get('content') or ''
    html = re.sub(r'<(script|style)[\s\S]*?</\1>', ' ', html)
    text = re.sub(r'<[^>]+>', ' ', html)
    import html as h
    return re.sub(r'\s+', ' ', h.unescape(text)).strip()


def decode(title, body, source_label):
    """Return {'titleKo', 'lines', 'layer', 'chronicle'} or None."""
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        return None
    src = '출처: %s\n제목: %s\n\n본문:\n%s' % (source_label, title, (body or '(본문 없음)')[:24000])
    try:
        res = _post({'model': MODEL, 'max_tokens': 800, 'system': SYSTEM,
                     'messages': [{'role': 'user', 'content': src}]}, key)
    except urllib.error.HTTPError as e:
        print('AI decode failed', e.code, e.read()[:300])
        return None
    except urllib.error.URLError as e:
        print('AI decode failed', e)
        return None
    text = ''.join(b.get('text', '') for b in res.get('content', []) if b.get('type') == 'text')
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        print('AI decode: no JSON')
        return None
    try:
        out = json.loads(m.group(0))
    except ValueError:
        print('AI decode: bad JSON')
        return None
    lines = [str(x).strip() for x in out.get('lines', []) if str(x).strip()][:3]
    if not lines or not out.get('titleKo'):
        return None
    layer = out.get('layer') if out.get('layer') in ('real', 'border', 'digital') else None
    return {'titleKo': str(out['titleKo']).strip()[:120], 'lines': lines, 'layer': layer, 'chronicle': bool(out.get('chronicle'))}


BANNER_SYSTEM = """어스2 공식 앱 상단 카운트다운 배너의 영어 제목을 한국어로 옮겨.
- 제목에 있는 말만 옮긴다. 설명, 추측, 권유를 덧붙이지 않는다.
- 게임 용어: Mentar → 멘타, Staker → 스테이커, Essence → 에센스, Tiles → 타일, Territory → 영토, Skin → 스킨, Perk → 혜택, Discount → 할인, Opening → 오픈, T3 → T3
- 결과 한 줄만, 따옴표 없이."""


def banner_ko(title):
    """Korean name for a countdown banner title, or None."""
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        return None
    try:
        res = _post({'model': MODEL, 'max_tokens': 60, 'system': BANNER_SYSTEM,
                     'messages': [{'role': 'user', 'content': title}]}, key)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print('banner_ko failed', e)
        return None
    text = ''.join(b.get('text', '') for b in res.get('content', []) if b.get('type') == 'text').strip()
    text = text.splitlines()[0].strip().strip('"“”') if text else ''
    return text[:60] or None
