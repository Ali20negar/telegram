# رندر گرافیک پست‌ها

`render-cover.js` یه فایل SVG رو با فونت Vazirmatn (فایل `fonts/Vazirmatn-Variable.woff2`، از پکیج npm رسمی `vazirmatn`، امبدشده به‌صورت base64 تا وابسته به دانلود لحظه‌ای از گوگل فونت نباشه) با headless Chromium به PNG تبدیل می‌کنه.

```
node scripts/render-cover.js path/to/cover.svg path/to/cover.png
```

نکات:
- رندر با `deviceScaleFactor: 2` انجام میشه تا متن شارپ باشه.
- تیتر اصلی هر گرافیک باید کاملاً فارسی باشه؛ کلمه‌های انگلیسی (اسم محصول، برند و...) رو توی برچسب/بج جدا بذار، نه وسط جمله — چون ترکیب فارسی+انگلیسی وسط یه جمله زیر قوانین بایدای یونیکد بد نمایش داده میشه.
- نیاز به Playwright global (`/opt/node22/lib/node_modules/playwright`) و کروم هدلس (`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`) داره که توی محیط اجرای این سشن از قبل نصبن.
