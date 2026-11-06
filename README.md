# terrasignal
TERRASIGNAL — 두 개의 지구. 하나의 좌표. METAFUNK AGENCY의 메타버스 방송국

사이트: https://metarobot1982.github.io/terrasignal/

## 구조
- `*.html` — 사이트 페이지 (`src/build.py`가 `src/design/*.dc.html`에서 만들어요. 직접 고치지 마세요)
- `data/*.json` — 사이트에 보이는 신호 데이터. 자동화는 이 파일만 바꿔요
  - `data/map.json` — 시그널 지도 핀(pins), 전역 송출(globals), 곧 열리는 시그널(countdowns)
  - `data/chronicle.json` — 개척 연대기 (세계 구조가 바뀐 날만)
- `js/dc-lite.js` — 페이지 화면 동작
- `src/design/` — 디자인 원본 (Claude Design 캔버스 "TERRASIGNAL 홈 디자인"과 같은 파일)

## 데이터 규칙
- 등급: CLEAR(공식) / WEAK(현장·커뮤니티) / NOISE(공식 발표 전)
- 층: 현실 지구(real/R) / 경계(border/B) / 디지털 지구(digital/D)
- 카운트다운 `endsAt`은 ISO 시각(예: `2026-11-10T12:00:00Z`). 비우면 "시각 확인 중"
- 할인·드롭은 사실만, 구매 권유 금지. 계정 잔액이 보이는 화면은 쓰지 않음
