// One-off (retry): open app.earth2.io logged out in a real browser, list JSON responses and visible banner/countdown text.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1400, height: 900 }, userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
  const seen = [];
  p.on('response', async r => {
    const u = r.url(), ct = r.headers()['content-type'] || '';
    if (/json/.test(ct) && !/google|facebook|sentry|mapbox|recaptcha/.test(u)) {
      let body = ''; try { body = (await r.text()).slice(0, 700); } catch (e) {}
      seen.push(r.status() + ' ' + u + '\n    ' + body.replace(/\s+/g, ' '));
    }
  });
  await p.goto('https://app.earth2.io/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(25000);
  console.log(seen.join('\n'));
  const txt = await p.evaluate(() => document.body.innerText);
  console.log('=== TEXT ===\n' + txt.slice(0, 3000));
  await p.screenshot({ path: 'probe.png' });
  await b.close();
})();
