#!/usr/bin/env python3
"""
Build one branded post-cover PNG for the "آخرین اخبار سئو" Telegram channel.

Usage:
  python3 scripts/make-cover.py \
    --kicker "فروشگاه آنلاین" \
    --headline "تیتر کاملا فارسی بدون کلمه انگلیسی وسطش" \
    --badge-win "Merchant API" --badge-lose "Content API" \
    --desc "یک جمله کوتاه توضیح" \
    --footer "DEADLINE SEP 1, 2026" \
    --out posts/2026-09-06/cover.png

Stat mode (no old-vs-new comparison) instead of --badge-win/--badge-lose:
  --stat-number "2.5B" --stat-label "کاربر ماهانه AI Overviews"

Variant selection: omit --variant to weighted-randomly pick one of the 10
templates (variants 1,2,5,6,7,9,10 get double weight per user preference).
Pass --variant N (1-10) to force a specific one.
"""
import argparse
import base64
import html
import os
import random
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(REPO_ROOT, "scripts/fonts/Vazirmatn-Variable.woff2")
LOGO_PATH = os.path.join(REPO_ROOT, "assets/channel-logo.png")
RENDER_JS = os.path.join(REPO_ROOT, "scripts/render-html-cover.js")

# variant_id -> weight. 1,2,5,6,7,9,10 preferred (weight 2), 3,4,8 normal (weight 1)
VARIANT_WEIGHTS = {1: 2, 2: 2, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 8: 1, 9: 2, 10: 2}

BASE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
@font-face {{
  font-family:'Vazirmatn';
  src:url(data:font/woff2;base64,{font_b64}) format('woff2-variations');
  font-weight:100 900;
}}
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;width:1200px;height:750px;overflow:hidden;font-family:'Vazirmatn',sans-serif;background:#000;}}
.canvas{{position:relative;width:1200px;height:750px;overflow:hidden;{canvas_bg}}}
.frame{{position:absolute;inset:14px;border:2px solid {frame_color};border-radius:32px;pointer-events:none;z-index:8;}}
.kicker{{position:absolute;top:46px;right:64px;color:{kicker_color};font-weight:800;font-size:23px;letter-spacing:2.5px;direction:rtl;z-index:7;text-shadow:0 2px 6px rgba(0,0,0,.7);}}
.headline{{position:absolute;top:84px;right:64px;left:64px;color:#ffffff;font-weight:800;font-size:{headline_size}px;line-height:1.32;text-align:right;direction:rtl;text-shadow:0 2px 4px rgba(0,0,0,.9), 0 8px 30px rgba(0,0,0,.75);z-index:7;}}
.underline{{position:absolute;top:{underline_top}px;right:180px;width:220px;height:6px;border-radius:3px;background:linear-gradient(90deg, rgba(232,176,75,0) 0%, {underline_color} 100%);z-index:7;}}
.glass-panel{{position:absolute;left:64px;right:64px;top:{panel_top}px;height:130px;border-radius:26px;z-index:6;display:flex;align-items:center;gap:22px;padding:0 40px;{panel_style}}}
.badge{{font-family:'Courier New',monospace;font-weight:700;font-size:28px;padding:16px 34px;border-radius:40px;white-space:nowrap;}}
.badge.win{{background:linear-gradient(180deg,#3fd9c9,#0e9089);color:#04231d;box-shadow:0 0 40px rgba(18,168,159,.65);}}
.badge.lose{{background:rgba(19,47,58,.55);color:#e6a196;border:2.5px solid #d3695a;position:relative;}}
.badge.lose::after{{content:'';position:absolute;left:10%;right:10%;top:50%;height:2px;background:#d3695a;transform:rotate(-8deg);}}
.arrow{{color:#eafaf7;font-size:34px;}}
.stat-number{{font-family:'Courier New',monospace;font-weight:700;font-size:56px;color:#3fd9c9;text-shadow:0 0 30px rgba(18,168,159,.6);}}
.stat-label{{font-size:24px;font-weight:600;color:#e9f4f2;direction:rtl;}}
.desc{{position:absolute;left:64px;right:64px;top:{desc_top}px;color:#e9f4f2;font-size:28px;font-weight:600;text-align:right;direction:rtl;z-index:7;text-shadow:0 2px 6px rgba(0,0,0,.85), 0 6px 18px rgba(0,0,0,.6);}}
.brandmark{{position:absolute;left:60px;bottom:52px;z-index:8;}}
.brandmark img{{width:64px;height:64px;border-radius:50%;box-shadow:0 4px 16px rgba(0,0,0,.55);}}
.footer{{position:absolute;right:64px;bottom:62px;color:{footer_color};font-family:'Courier New',monospace;font-size:19px;font-weight:700;letter-spacing:1px;direction:rtl;z-index:7;text-shadow:0 2px 6px rgba(0,0,0,.7);}}
</style>
</head>
<body>
<div class="canvas">
  {extra_bg_html}
  <div style="position:absolute;inset:0;background:linear-gradient(225deg, rgba(0,0,0,.4) 0%, rgba(0,0,0,0) 42%);z-index:3;"></div>
  <div style="position:absolute;left:0;right:0;bottom:0;height:260px;background:linear-gradient(0deg, rgba(0,0,0,.35) 0%, rgba(0,0,0,0) 100%);z-index:3;"></div>
  <div class="frame"></div>
  <div class="kicker">{kicker_prefix}{kicker}</div>
  <div class="headline">{headline}</div>
  <div class="underline"></div>
  <div class="glass-panel">{panel_content}</div>
  <div class="desc">{desc}</div>
  <div class="brandmark"><img src="data:image/png;base64,{logo_b64}"></div>
  <div class="footer">{footer_prefix}{footer}</div>
</div>
</body></html>
"""

VARIANTS = {
    1: dict(
        canvas_bg="background:linear-gradient(135deg,#050a12,#01050a);",
        extra_bg_html="""
        <div style="position:absolute;width:520px;height:520px;left:-120px;top:-140px;background:#12a89f;border-radius:50%;filter:blur(110px);opacity:.55;"></div>
        <div style="position:absolute;width:480px;height:480px;right:-140px;top:-100px;background:#e8b04b;border-radius:50%;filter:blur(120px);opacity:.4;"></div>
        <div style="position:absolute;width:560px;height:560px;left:30%;bottom:-260px;background:#1c6fa8;border-radius:50%;filter:blur(130px);opacity:.5;"></div>
        """,
        panel_style="backdrop-filter:blur(22px) saturate(180%);-webkit-backdrop-filter:blur(22px) saturate(180%);background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.22);box-shadow:0 12px 40px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.25);",
        frame_color="rgba(232,176,75,.35)", kicker_color="#e8b04b", underline_color="#e8b04b",
        footer_color="#c99a52", kicker_prefix="— ", footer_prefix="• ",
    ),
    2: dict(
        canvas_bg="background:radial-gradient(ellipse at 70% 0%, #0c3040 0%, #030a10 60%);",
        extra_bg_html="""
        <div style="position:absolute;inset:0;background-image:linear-gradient(rgba(18,168,159,.18) 1px, transparent 1px),linear-gradient(90deg, rgba(18,168,159,.18) 1px, transparent 1px);background-size:40px 40px;transform:perspective(600px) rotateX(55deg) translateY(120px) scale(1.6);transform-origin:center bottom;opacity:.55;"></div>
        <div style="position:absolute;width:600px;height:600px;right:-160px;top:-220px;background:#12a89f;border-radius:50%;filter:blur(140px);opacity:.35;"></div>
        """,
        panel_style="backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);background:rgba(6,20,26,.55);border:1px solid rgba(18,168,159,.45);box-shadow:0 0 40px rgba(18,168,159,.25), inset 0 1px 0 rgba(255,255,255,.12);",
        frame_color="rgba(18,168,159,.4)", kicker_color="#7fd9cd", underline_color="#12a89f",
        footer_color="#6fb3ac", kicker_prefix="// ", footer_prefix="> ",
    ),
    3: dict(
        canvas_bg="background:linear-gradient(160deg,#08222c,#020a0e);",
        extra_bg_html="""
        <svg style="position:absolute;inset:0;opacity:.28" width="1200" height="750" viewBox="0 0 1200 750">
          <defs><pattern id="circ" width="120" height="120" patternUnits="userSpaceOnUse">
            <path d="M0 60 H40 V20 H90" stroke="#3fd9c9" stroke-width="2" fill="none"/>
            <path d="M120 90 H80 V110" stroke="#3fd9c9" stroke-width="2" fill="none"/>
            <circle cx="40" cy="20" r="4" fill="#e8b04b"/>
            <circle cx="90" cy="20" r="3" fill="#3fd9c9"/>
            <circle cx="80" cy="110" r="3" fill="#3fd9c9"/>
          </pattern></defs>
          <rect width="1200" height="750" fill="url(#circ)"/>
        </svg>
        <div style="position:absolute;width:500px;height:500px;right:-100px;top:-160px;background:#e8b04b;border-radius:50%;filter:blur(150px);opacity:.22;"></div>
        """,
        panel_style="backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);background:rgba(8,30,38,.6);border:1px solid rgba(232,176,75,.4);box-shadow:0 10px 30px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.1);",
        frame_color="rgba(232,176,75,.4)", kicker_color="#e8b04b", underline_color="#e8b04b",
        footer_color="#c99a52", kicker_prefix="— ", footer_prefix="• ",
    ),
    4: dict(
        canvas_bg="background:linear-gradient(140deg,#0a1420,#02060a);",
        extra_bg_html="""
        <div style="position:absolute;inset:-200px;background:linear-gradient(115deg, transparent 30%, rgba(63,217,201,.35) 42%, rgba(232,176,75,.3) 50%, rgba(120,180,255,.3) 58%, transparent 70%);filter:blur(6px);"></div>
        <div style="position:absolute;width:600px;height:600px;left:-160px;bottom:-220px;background:#1c6fa8;border-radius:50%;filter:blur(140px);opacity:.35;"></div>
        """,
        panel_style="backdrop-filter:blur(24px) saturate(200%);-webkit-backdrop-filter:blur(24px) saturate(200%);background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.3);box-shadow:0 12px 44px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.35);",
        frame_color="rgba(255,255,255,.25)", kicker_color="#9fe8de", underline_color="#e8b04b",
        footer_color="#a9c9c4", kicker_prefix="✦ ", footer_prefix="✦ ",
    ),
    5: dict(
        canvas_bg="background:linear-gradient(135deg,#0c3446,#071822);",
        extra_bg_html="""
        <div style="position:absolute;width:520px;height:520px;right:-100px;top:-180px;background:#12a89f;border-radius:50%;filter:blur(100px);opacity:.6;"></div>
        <div style="position:absolute;width:420px;height:420px;left:-80px;top:20px;background:#e8b04b;border-radius:50%;filter:blur(100px);opacity:.4;"></div>
        <div style="position:absolute;width:560px;height:560px;right:-140px;bottom:-260px;background:#0d6b8a;border-radius:50%;filter:blur(110px);opacity:.65;"></div>
        <div style="position:absolute;width:380px;height:380px;left:-60px;bottom:-160px;background:#12a89f;border-radius:50%;filter:blur(100px);opacity:.4;"></div>
        """,
        panel_style="backdrop-filter:blur(20px) saturate(160%);-webkit-backdrop-filter:blur(20px) saturate(160%);background:rgba(4,15,20,.35);border:1px solid rgba(255,255,255,.18);box-shadow:0 10px 36px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.2);",
        frame_color="rgba(232,176,75,.3)", kicker_color="#e8b04b", underline_color="#e8b04b",
        footer_color="#c99a52", kicker_prefix="— ", footer_prefix="• ",
    ),
    6: dict(
        canvas_bg="background:linear-gradient(160deg,#070d14,#010305);",
        extra_bg_html="""
        <div style="position:absolute;width:1600px;height:90px;left:-200px;top:60px;background:linear-gradient(90deg, transparent, rgba(255,255,255,.5), transparent);filter:blur(18px);transform:rotate(-18deg);opacity:.55;"></div>
        <div style="position:absolute;width:1600px;height:14px;left:-200px;top:120px;background:linear-gradient(90deg, transparent, rgba(120,220,255,.6), rgba(232,176,75,.6), rgba(63,217,201,.6), transparent);transform:rotate(-18deg);opacity:.7;"></div>
        <div style="position:absolute;width:500px;height:500px;right:-140px;bottom:-200px;background:#12a89f;border-radius:50%;filter:blur(130px);opacity:.3;"></div>
        """,
        panel_style="backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.22);box-shadow:0 10px 36px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.25);",
        frame_color="rgba(255,255,255,.22)", kicker_color="#e8b04b", underline_color="#e8b04b",
        footer_color="#b9c4c9", kicker_prefix="— ", footer_prefix="• ",
    ),
    7: dict(
        canvas_bg="background:linear-gradient(135deg,#0a2b38,#04121a);",
        extra_bg_html="""
        <div style="position:absolute;width:900px;height:220px;left:150px;top:250px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:30px;transform:rotate(-4deg);"></div>
        <div style="position:absolute;width:900px;height:220px;left:170px;top:270px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:30px;transform:rotate(3deg);"></div>
        <div style="position:absolute;width:480px;height:480px;right:-120px;top:-160px;background:#e8b04b;border-radius:50%;filter:blur(130px);opacity:.25;"></div>
        <div style="position:absolute;width:480px;height:480px;left:-120px;bottom:-200px;background:#12a89f;border-radius:50%;filter:blur(130px);opacity:.35;"></div>
        """,
        panel_style="backdrop-filter:blur(20px) saturate(170%);-webkit-backdrop-filter:blur(20px) saturate(170%);background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.28);box-shadow:0 14px 44px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.3);",
        frame_color="rgba(255,255,255,.2)", kicker_color="#9fe8de", underline_color="#e8b04b",
        footer_color="#a9c9c4", kicker_prefix="— ", footer_prefix="• ",
    ),
    8: dict(
        canvas_bg="background:radial-gradient(ellipse at 75% 10%, #0d1e2c 0%, #020508 55%);",
        extra_bg_html="""
        <div style="position:absolute;inset:0;background-image:radial-gradient(1.5px 1.5px at 20px 30px, rgba(255,255,255,.8), transparent),radial-gradient(1.5px 1.5px at 120px 90px, rgba(255,255,255,.6), transparent),radial-gradient(1px 1px at 220px 40px, rgba(255,255,255,.7), transparent),radial-gradient(1.5px 1.5px at 320px 150px, rgba(255,255,255,.5), transparent),radial-gradient(1px 1px at 420px 60px, rgba(255,255,255,.6), transparent),radial-gradient(1.5px 1.5px at 520px 200px, rgba(255,255,255,.5), transparent),radial-gradient(1px 1px at 620px 90px, rgba(255,255,255,.7), transparent),radial-gradient(1.5px 1.5px at 720px 40px, rgba(255,255,255,.5), transparent),radial-gradient(1px 1px at 820px 180px, rgba(255,255,255,.6), transparent),radial-gradient(1.5px 1.5px at 920px 70px, rgba(255,255,255,.5), transparent),radial-gradient(1px 1px at 1020px 140px, rgba(255,255,255,.6), transparent),radial-gradient(1.5px 1.5px at 1120px 50px, rgba(255,255,255,.5), transparent);background-size:1200px 750px;opacity:.8;"></div>
        <div style="position:absolute;width:560px;height:560px;right:-160px;top:-220px;background:#e8b04b;border-radius:50%;filter:blur(150px);opacity:.3;"></div>
        """,
        panel_style="backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.16);box-shadow:0 10px 34px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.2);",
        frame_color="rgba(232,176,75,.3)", kicker_color="#e8b04b", underline_color="#e8b04b",
        footer_color="#c99a52", kicker_prefix="✦ ", footer_prefix="✦ ",
    ),
    9: dict(
        canvas_bg="background:linear-gradient(160deg,#062430,#020a0e);",
        extra_bg_html="""
        <svg style="position:absolute;bottom:0;left:0;opacity:.35" width="1200" height="300" viewBox="0 0 1200 300">
          <path d="M0 150 Q 100 50 200 150 T 400 150 T 600 150 T 800 150 T 1000 150 T 1200 150" stroke="#12a89f" stroke-width="3" fill="none"/>
          <path d="M0 190 Q 100 110 200 190 T 400 190 T 600 190 T 800 190 T 1000 190 T 1200 190" stroke="#e8b04b" stroke-width="2" fill="none" opacity=".7"/>
          <path d="M0 220 Q 100 160 200 220 T 400 220 T 600 220 T 800 220 T 1000 220 T 1200 220" stroke="#3fd9c9" stroke-width="1.5" fill="none" opacity=".5"/>
        </svg>
        <div style="position:absolute;width:500px;height:500px;right:-140px;top:-200px;background:#12a89f;border-radius:50%;filter:blur(140px);opacity:.3;"></div>
        """,
        panel_style="backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);background:rgba(6,26,32,.55);border:1px solid rgba(18,168,159,.4);box-shadow:0 10px 32px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.15);",
        frame_color="rgba(18,168,159,.35)", kicker_color="#7fd9cd", underline_color="#12a89f",
        footer_color="#6fb3ac", kicker_prefix="~ ", footer_prefix="~ ",
    ),
    10: dict(
        canvas_bg="background:linear-gradient(160deg,#0a0806,#010101);",
        extra_bg_html="""
        <div style="position:absolute;inset:-100px;background:repeating-linear-gradient(35deg, transparent 0 60px, rgba(232,176,75,.08) 60px 62px);"></div>
        <div style="position:absolute;width:520px;height:520px;right:-140px;top:-200px;background:#e8b04b;border-radius:50%;filter:blur(150px);opacity:.28;"></div>
        <div style="position:absolute;width:420px;height:420px;left:-100px;bottom:-180px;background:#c9903a;border-radius:50%;filter:blur(140px);opacity:.22;"></div>
        """,
        panel_style="backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);background:rgba(20,15,5,.5);border:1.5px solid rgba(232,176,75,.55);box-shadow:0 12px 40px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,220,150,.25);",
        frame_color="rgba(232,176,75,.55)", kicker_color="#f0c56e", underline_color="#e8b04b",
        footer_color="#d4ab5f", kicker_prefix="✧ ", footer_prefix="✧ ",
    ),
}


def pick_variant():
    ids = list(VARIANT_WEIGHTS.keys())
    weights = [VARIANT_WEIGHTS[i] for i in ids]
    return random.choices(ids, weights=weights, k=1)[0]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kicker", required=True, help="Small label top-right (Persian)")
    p.add_argument("--headline", required=True, help="Pure-Persian headline, no inline Latin words")
    p.add_argument("--badge-win", help="Green glowing badge text (English ok, short)")
    p.add_argument("--badge-lose", help="Red struck-through badge text (English ok, short)")
    p.add_argument("--stat-number", help="Big stat number instead of badges, e.g. 2.5B")
    p.add_argument("--stat-label", help="Short Persian label under the stat number")
    p.add_argument("--desc", required=True, help="Short Persian description line")
    p.add_argument("--footer", required=True, help="Footer text after the bullet, e.g. a date or category")
    p.add_argument("--out", required=True, help="Output PNG path")
    p.add_argument("--variant", type=int, choices=range(1, 11), help="Force a specific variant 1-10")
    args = p.parse_args()

    variant_id = args.variant or pick_variant()
    v = VARIANTS[variant_id]

    if args.badge_win or args.badge_lose:
        panel_content = ""
        if args.badge_win:
            panel_content += f'<div class="badge win">{html.escape(args.badge_win)}</div>'
        if args.badge_win and args.badge_lose:
            panel_content += '<div class="arrow">&#8592;</div>'
        if args.badge_lose:
            panel_content += f'<div class="badge lose">{html.escape(args.badge_lose)}</div>'
    elif args.stat_number:
        panel_content = (
            f'<div class="stat-number">{html.escape(args.stat_number)}</div>'
            f'<div class="stat-label">{html.escape(args.stat_label or "")}</div>'
        )
    else:
        sys.exit("error: pass either --badge-win/--badge-lose or --stat-number")

    # Headlines longer than ~30 chars tend to wrap to 2 lines at the large
    # size; shrink the font and push everything below it down so the gold
    # underline and glass panel never collide with a wrapped second line.
    if len(args.headline) > 30:
        headline_size, underline_top, panel_top, desc_top = 40, 222, 310, 474
    else:
        headline_size, underline_top, panel_top, desc_top = 52, 175, 288, 452

    with open(FONT_PATH, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode()
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()

    html_out = BASE_TEMPLATE.format(
        font_b64=font_b64,
        logo_b64=logo_b64,
        kicker=html.escape(args.kicker),
        headline=html.escape(args.headline),
        desc=html.escape(args.desc),
        footer=html.escape(args.footer),
        panel_content=panel_content,
        headline_size=headline_size,
        underline_top=underline_top,
        panel_top=panel_top,
        desc_top=desc_top,
        **v,
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
        tmp.write(html_out)
        tmp_path = tmp.name

    try:
        subprocess.run(["node", RENDER_JS, tmp_path, args.out], check=True)
    finally:
        os.unlink(tmp_path)

    print(f"variant used: {variant_id}")
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
