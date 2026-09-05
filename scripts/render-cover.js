const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const fs = require('fs');

const [,, svgFile, pngFile] = process.argv;
if (!svgFile || !pngFile) {
  console.error('usage: node render.js <in.svg> <out.png>');
  process.exit(1);
}

const FONT_PATH = path.join(__dirname, 'fonts/Vazirmatn-Variable.woff2');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1200, height: 750 }, deviceScaleFactor: 2 });

  const fontBase64 = fs.readFileSync(FONT_PATH).toString('base64');
  const svgContent = fs.readFileSync(svgFile, 'utf8');

  const html = `
    <html><head><style>
      @font-face {
        font-family: 'Vazirmatn';
        src: url(data:font/woff2;base64,${fontBase64}) format('woff2-variations');
        font-weight: 100 900;
      }
      html,body{margin:0;padding:0;}
      text{font-family:'Vazirmatn', sans-serif !important;}
    </style></head>
    <body>${svgContent}</body></html>
  `;
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(150);
  await page.screenshot({ path: pngFile });
  await browser.close();
  console.log('done:', pngFile);
})();
