import assert from 'node:assert/strict';
import puppeteer from 'puppeteer-core';

const base = new URL('http://127.0.0.1:8765/sarkarialert/');
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-background-networking']
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.setRequestInterception(true);
  page.on('request', req => {
    const url = new URL(req.url());
    if (url.origin === base.origin || ['data:', 'blob:', 'about:'].includes(url.protocol)) {
      req.continue();
    } else {
      req.abort();
    }
  });
  async function open(path) {
    const res = await page.goto(new URL(path, base).href, {waitUntil:'domcontentloaded',timeout:20000});
    assert.equal(res.status(), 200, path);
    await page.waitForSelector('main h1', {timeout:10000});
  }
  await page.setViewport({width: 1280, height: 800});
  await open('');
  const nav = await page.$eval('nav a[href$="tools/"]', a => a.textContent);
  assert.ok(nav.includes('Student Tools') && nav.includes('विद्यार्थी उपयोगी उपकरण'));
  await open('category/latest-jobs/');
  const first = await page.$eval('li[data-post] a[href*="posts/"]', a => a.href);
  assert.ok(first.startsWith(base.href));
  await open(first.slice(base.href.length));
  await open('tools/');
  await page.click('[data-tab="t-age"]');
  await page.waitForSelector('#age-go', {visible: true});
  await page.$eval('#age-dob', el => el.value = '2000-01-01');
  await page.$eval('#age-ason', el => el.value = '2026-01-01');
  await page.click('#age-go');
  assert.match(await page.$eval('#age-out', el => el.textContent), /26 वर्ष, 0 महीने, 0 दिन/);
  await page.setViewport({width: 390, height: 844});
  await open('');
  await open('tools/');
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log('Browser smoke passed: homepage, jobs, post, student tools, age calculator, mobile viewport.');
} finally {
  await browser.close();
}
