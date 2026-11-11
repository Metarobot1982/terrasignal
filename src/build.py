#!/usr/bin/env python3
"""Build TERRASIGNAL static pages from the Claude Design .dc.html sources.

Usage: python3 src/build.py   (sources in src/design, pages written to the repo root)
Writes index.html, signal.html, map.html, dive.html, guide.html, item.html,
chronicle.html, prologue.html next to this script.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'design')
OUT = os.path.dirname(HERE)  # site root (repo root)
SITE = 'https://metarobot1982.github.io/terrasignal/'

PAGES = {
    'Main.dc.html': ('index.html', 'TERRASIGNAL — 두 개의 지구. 하나의 좌표.', '경계 너머 디지털 지구의 신호를 이쪽 지구로 송출하는 METAFUNK AGENCY의 방송국.'),
    'RxDetail.dc.html': ('signal.html', '수신 기록 · TERRASIGNAL', '경계 너머에서 도착한 신호의 3줄 해독과 원문 출처.'),
    'SignalMap.dc.html': ('map.html', '시그널 지도 · TERRASIGNAL', '신호가 도착한 좌표. 현실 지구와 디지털 지구, 그 사이의 경계.'),
    'SignalDive.dc.html': ('dive.html', '시그널 다이브 · TERRASIGNAL', '신호를 따라 좌표로. 하나의 좌표, 두 개의 지구.'),
    'Guide.dc.html': ('guide.html', '수신 가이드 · TERRASIGNAL', '디지털 지구에서 살아가는 법. 아이템과 시스템을 모은 살아있는 도감.'),
    'GuideItem.dc.html': ('item.html', '백팩 · 수신 가이드 · TERRASIGNAL', '백팩을 만드는 순서와 재료, 주의할 점.'),
    'Chronicle.dc.html': ('chronicle.html', '개척 연대기 · TERRASIGNAL', '디지털 지구가 깨어난 날부터의 기록.'),
    'Prologue.dc.html': ('prologue.html', '프롤로그 · TERRASIGNAL', '지구는 하나뿐이라고 믿었다. TERRASIGNAL의 프롤로그.'),
}

ASSETS = {
    '1cf215a3977029b64faf8cab9aef9688': 'assets/1cf215a3977029b64faf8cab9aef9688.jpg',
    '81bc16718fe06a9909a32dd75a0ac407': 'assets/81bc16718fe06a9909a32dd75a0ac407.webp',
    'ac50af9688746efd633f474b3231c7fc': 'assets/ac50af9688746efd633f474b3231c7fc.jpg',
    'c2a6da08f7402bf8c326362a0db85b84': 'assets/c2a6da08f7402bf8c326362a0db85b84.jpg',
    'cbcf6a44b5e02698271dc91cdb3d9b44': 'assets/cbcf6a44b5e02698271dc91cdb3d9b44.mp4',
    'd4e097ee3e19c66ce1a25f782eece347': 'assets/d4e097ee3e19c66ce1a25f782eece347.webp',
    'ea9e760d62745312f367290e811d7de7': 'assets/ea9e760d62745312f367290e811d7de7.webp',
    'f9dabe0b371fffeb0818b70b009d8797': 'assets/f9dabe0b371fffeb0818b70b009d8797.webp',
}

DATA = {
    'Main.dc.html': {'signals': 'data/signals.json', 'map': 'data/map.json'},
    'RxDetail.dc.html': {'signals': 'data/signals.json'},
    'SignalMap.dc.html': {'map': 'data/map.json'},
    'Chronicle.dc.html': {'chronicle': 'data/chronicle.json'},
}

NAV = {
    '시그널 수신': 'index.html#rx',
    '시그널 지도': 'map.html',
    '수신 가이드': 'guide.html',
    '개척 연대기': 'chronicle.html',
    '프롤로그': 'prologue.html',
    '시그널 보내기': 'index.html#tx-you',
}

# (keyword in anchor inner text, target)
LINK_RULES = [
    ('지도 열기', 'map.html'),
    ('시그널 지도에서 보기', 'map.html'),
    ('프롤로그 전체 보기', 'prologue.html'),
    ('시그널 열기', 'signal.html'),
    ('수신 기록 보기', 'signal.html'),
    ('리얼리티 스레드 4', 'signal.html'),
    ('오늘의 신호 수신하기', 'index.html#rx'),
    ('내 시그널 보내기', 'index.html#tx-you'),
    ('제보 보내기', 'index.html#tx-you'),
    ('{{it.name}}', 'item.html'),
    ('제작과 아이템 가이드', 'guide.html'),
]

EXTRA_CSS = """
x-dc,template{display:none}
@media (max-width:1560px){.ts header span[style*="border-left: 1px solid #23263a"]{display:none}}
html{scroll-behavior:smooth}
@media (max-width:900px){
  .ts .hdrnav{display:flex!important;width:100%;margin-left:0!important;overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .ts .hdrnav::-webkit-scrollbar{display:none}
}
"""


def convert(src_name, out_name, title, desc):
    h = open(os.path.join(SRC, src_name), encoding='utf-8').read()
    helmet = re.search(r'<helmet>([\s\S]*?)</helmet>', h).group(1)
    body_tpl = re.search(r'<x-dc>([\s\S]*?)</x-dc>', h).group(1)
    body_tpl = re.sub(r'<helmet>[\s\S]*?</helmet>', '', body_tpl)
    sm = re.search(r'<script type="text/x-dc" data-dc-script data-props=\'([\s\S]*?)\'>([\s\S]*?)</script>', h)
    props_json, comp_js = sm.group(1), sm.group(2)
    script = '<script type="application/json" id="dc-props">' + props_json + '</script>\n<script>\n' + comp_js.strip() + '\nwindow.TSComponent = Component;\n</script>'

    def fix(s):
        for k, v in ASSETS.items():
            s = s.replace('/_blob/' + k, v)
        return s

    helmet, body_tpl = fix(helmet), fix(body_tpl)

    # nav hrefs: rebuild cleanly
    def nav_clean(nm):
        block = nm.group(1)
        def one(m):
            open_tag, inner = m.group(1), m.group(2)
            label = re.sub(r'<[^>]+>', '', inner).strip()
            if label in NAV:
                open_tag = re.sub(r'href="[^"]*"', 'href="%s"' % NAV[label], open_tag, count=1)
            return open_tag + inner + '</a>'
        return re.sub(r'(<a [^>]*>)([\s\S]*?)</a>', one, block)
    body_tpl = re.sub(r'(<nav class="hdrnav"[\s\S]*?</nav>)', nav_clean, body_tpl, count=1)

    body_tpl = body_tpl.replace('href="#top"', 'href="index.html"')

    def link_sub(m):
        open_tag, inner = m.group(1), m.group(2)
        if 'href="#"' not in open_tag:
            return m.group(0)
        text = inner
        for key, target in LINK_RULES:
            if key in text or key in open_tag:
                return open_tag.replace('href="#"', 'href="%s"' % target, 1) + inner + '</a>'
        crumbs = re.sub(r'<[^>]+>', '', inner).strip()
        if crumbs == '홈':
            return open_tag.replace('href="#"', 'href="index.html"', 1) + inner + '</a>'
        if crumbs in ('수신 기록',):
            return open_tag.replace('href="#"', 'href="index.html#rx"', 1) + inner + '</a>'
        if crumbs in ('수신 가이드',):
            return open_tag.replace('href="#"', 'href="guide.html"', 1) + inner + '</a>'
        return m.group(0)
    body_tpl = re.sub(r'(<a [^>]*>)([\s\S]*?)</a>', link_sub, body_tpl)

    if out_name != 'index.html':
        for a in ('#rx', '#tx-you', '#ch', '#portal', '#prologue', '#map'):
            body_tpl = body_tpl.replace('href="%s"' % a, 'href="index.html%s"' % a)

    mapbox_tag = "<script>window.TS_MAPBOX = 'pk.eyJ1IjoibWV0YXJvYm90MTk4MiIsImEiOiJjbXdidXJmamcwMnkxMnpva2ZlbWthY29pIn0.b837yBqRofBDs20_pEgngg';</script>\n" if src_name == 'SignalDive.dc.html' else ''
    data_tag = ('<script>window.TS_DATA = %s;</script>\n' % json.dumps(DATA[src_name])) if src_name in DATA else ''
    head = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="TERRASIGNAL">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}{'' if out_name == 'index.html' else out_name}">
<link rel="canonical" href="{SITE}{'' if out_name == 'index.html' else out_name}">
<meta property="og:image" content="{SITE}assets/share.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b0c14">
<link rel="icon" href="favicon.ico">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
{helmet.strip()}
<style>{EXTRA_CSS}</style>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "461cfeaefff848cda186328d4f27ed23"}}'></script>
{mapbox_tag}{data_tag}<script src="js/dc-lite.js"></script>
</head>
<body>
<div id="dc-root"></div>
<template id="dc-tpl">{body_tpl}</template>
{script}
</body>
</html>
'''
    open(os.path.join(OUT, out_name), 'w', encoding='utf-8').write(head)
    return out_name


if __name__ == '__main__':
    for src, (out, title, desc) in PAGES.items():
        print('built', convert(src, out, title, desc))
