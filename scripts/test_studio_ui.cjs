// Run against an existing local API server with Playwright on NODE_PATH.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const errors = [];
    const requests = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/chat', async route => {
      requests.push(route.request().postDataJSON());
      await route.fulfill({ contentType: 'text/event-stream', body:
        'data: {"type":"status","message":"Council review","run_id":"qa"}\n\n' +
        'data: {"type":"token","chunk":"Verified browser answer"}\n\n' +
        'data: {"type":"done","citations":[]}\n\n' });
    });
    await page.goto(process.env.M1_TEST_URL || 'http://127.0.0.1:8089');
    await page.waitForLoadState('networkidle');
    await page.locator('[data-nav="chat"]').click();
    await page.locator('#chatmode').waitFor();
    assert.equal(await page.locator('#chatmode').inputValue(), 'full');
    await page.locator('#chatin').fill('Remember SQLite');
    await page.locator('#chatin').press('Enter');
    await page.locator('.msg.bot .prose').last().getByText('Verified browser answer').waitFor();
    assert.equal(requests[0].mode, 'full');
    assert.deepEqual(requests[0].messages, []);
    await page.locator('#chatmode').selectOption('quick');
    await page.locator('#chatin').fill('What database?');
    await page.locator('#chatin').press('Enter');
    await page.waitForFunction(() => document.querySelectorAll('.msg.bot').length === 2 && !S.chatBusy);
    assert.equal(requests[1].mode, 'quick');
    assert.equal(requests[1].messages[0].content, 'Remember SQLite');
    assert.equal(requests[1].messages[1].role, 'assistant');
    assert.equal(await page.locator('#chatmode').inputValue(), 'quick');
    await page.unroute('**/chat');
    await page.route('**/chat', route => route.fulfill({ status: 503,
      contentType: 'application/json', body: JSON.stringify({detail:'Live backend unavailable for QA'}) }));
    await page.locator('#chatmode').selectOption('full');
    await page.locator('#chatin').fill('Check error display');
    await page.locator('#chatin').press('Enter');
    await page.getByText(/Live backend unavailable for QA/).waitFor();
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    const sendBox = await page.getByRole('button', {name:'Send', exact:true}).boundingBox();
    assert.ok(sendBox && sendBox.x + sendBox.width <= 390, 'Send button must remain visible on mobile');
    assert.equal(await page.evaluate(() => {
      const tip=document.createElement('div');
      const cv=document.createElement('canvas');
      const graph={cv,tip,N:[{id:'<img src=x onerror="window.xss=1">',type:'<svg onload="window.xss=1">',x:0,y:0}],big:false};
      Graph.prototype.move.call(graph,{clientX:0,clientY:0});
      return tip.querySelector('img,svg')===null && tip.textContent.includes('<img');
    }), true, 'Graph tooltips must render untrusted titles as text');
    await page.screenshot({path: '.test-tmp/studio-full-chat.png', fullPage: true});
    assert.deepEqual(errors, []);
    console.log('Studio browser QA passed: full default, quick opt-in, history, HTTP error display, mobile layout, graph XSS defense; no page errors.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
