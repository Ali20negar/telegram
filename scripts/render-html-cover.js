const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');

const [,, htmlFile, pngFile] = process.argv;
if (!htmlFile || !pngFile) {
  console.error('usage: node render-html-cover.js <in.html> <out.png>');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1200, height: 750 }, deviceScaleFactor: 2 });
  const html = fs.readFileSync(htmlFile, 'utf8');
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(150);
  await page.screenshot({ path: pngFile });
  await browser.close();
  console.log('done:', pngFile);
})();
