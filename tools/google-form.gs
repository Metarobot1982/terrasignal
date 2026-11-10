/**
 * TERRASIGNAL · 시그널 보내기 — Google Apps Script
 *
 * 1) script.google.com → 새 프로젝트 → 이 코드를 전부 붙여넣기 → 저장
 * 2) 위쪽 함수 목록에서 setup 선택 → 실행 → 권한 허용
 *    → 실행 로그에 "폼 공유 주소"가 나와요. 그 주소를 Claude에게 보내주세요.
 * 3) (2단계) 디스코드 #시청자-수신 채널의 웹후크 주소를 아래 WEBHOOK_URL에 넣고 저장하면,
 *    폼에 들어온 시그널이 그 채널로 자동 전달돼요. 웹후크 주소는 누구에게도 보내지 마세요.
 */
const WEBHOOK_URL = '';

const TITLE = 'TERRASIGNAL · 시그널 보내기';
const DESCRIPTION = [
  '디지털 지구에서 궁금한 것, 직접 본 것을 TERRASIGNAL로 보내주세요.',
  '보내주신 내용은 운영자가 확인한 뒤 방송·홈페이지에 소개될 수 있어요. 소개할 때 닉네임과 도시까지만 공개하고, 그 밖의 개인 정보는 받지 않아요.',
  '레퍼럴 코드 홍보, 구매 권유, 다른 사람의 개인 정보는 소개하지 않아요.',
  'TERRASIGNAL은 METAFUNK AGENCY의 비공식 팬 방송국이며 Earth 2 공식 채널이 아니에요.'
].join('\n');

function setup() {
  const form = FormApp.create(TITLE);
  form.setDescription(DESCRIPTION);
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(true);
  form.setConfirmationMessage('시그널을 받았어요! 운영자가 확인한 뒤 방송이나 홈페이지에 소개될 수 있어요. — TERRASIGNAL');
  form.addTextItem().setTitle('닉네임 (방송에 나와도 되는 이름)').setRequired(true);
  form.addMultipleChoiceItem().setTitle('무엇을 보내시나요?')
    .setChoiceValues(['질문', '현장 제보', '버그·변화 발견', '기타']).setRequired(true);
  form.addParagraphTextItem().setTitle('내용').setRequired(true);
  form.addTextItem().setTitle('어디서 봤나요? (도시나 나라, 또는 E2V1 좌표)');
  form.addTextItem().setTitle('참고 링크 (스크린샷·영상 주소)');
  ScriptApp.newTrigger('onSubmit').forForm(form).onFormSubmit().create();
  Logger.log('폼 공유 주소: ' + form.getPublishedUrl());
  Logger.log('폼 편집 주소: ' + form.getEditUrl());
}

function oneLine_(s, max) {
  return String(s || '').replace(/@(everyone|here)/g, '@​$1').replace(/\s+/g, ' ').trim().slice(0, max);
}

function onSubmit(e) {
  if (!WEBHOOK_URL) return;
  const items = e.response.getItemResponses();
  const v = items.map(function (x) { return x.getResponse(); });
  const body = String(v[2] || '').replace(/@(everyone|here)/g, '@​$1').slice(0, 1400);
  const text = [
    '[TS-VIEWER]',
    '닉네임: ' + oneLine_(v[0], 40),
    '종류: ' + oneLine_(v[1], 20),
    '장소: ' + oneLine_(v[3], 80),
    '링크: ' + oneLine_(v[4], 300),
    '내용:',
    body
  ].join('\n');
  UrlFetchApp.fetch(WEBHOOK_URL, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ username: 'TERRASIGNAL 시그널 보내기', content: text.slice(0, 1990), allowed_mentions: { parse: [] } }),
    muteHttpExceptions: true
  });
}
