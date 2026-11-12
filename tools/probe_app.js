// One-off: are the skin store and territory pages readable logged out? List their JSON sources.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const hash of ['#skins', '#territories', '#territory-releases', '#governance']) {
    const p = await b.newPage({ viewport: { width: 1400, height: 900 }, userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' });
    const seen = [];
    p.on('response', async r => {
      const u = r.url(), ct = r.headers()['content-type'] || '';
      if (/json/.test(ct) && /earth2/.test(u) && !/sprite|materials/.test(u)) {
        let body = ''; try { body = (await r.text()).slice(0, 1500); } catch (e) {}
        const req = r.request(); seen.push(r.status() + ' ' + req.method() + ' ' + u + '\n    REQ ' + (req.postData() || '').slice(0, 600) + '\n    RES ' + body.replace(/\s+/g, ' '));
      }
    });
    await p.goto('https://app.earth2.io/' + hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(20000);
    console.log('######## ' + hash); console.log(seen.join('\n'));
    console.log('--- TEXT ---\n' + (await p.evaluate(() => document.body.innerText)).slice(0, 1500));
    await p.close();
  }
  await b.close();
})();
