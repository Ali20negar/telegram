import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const FEEDS = [
  "https://www.seroundtable.com/index.xml",
  "https://www.searchenginejournal.com/feed/",
  "https://searchengineland.com/feed/",
];

const RLM = "‏";
function rtl(line: string): string {
  return line ? RLM + line : line;
}

function xmlTag(block: string, tag: string): string {
  const m = block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i"));
  if (!m) return "";
  return m[1].replace(/<!\[CDATA\[([\s\S]*?)\]\]>/, "$1").trim();
}

interface FeedItem {
  title: string;
  link: string;
  description: string;
  pubDate: Date;
}

async function fetchFeedItems(url: string): Promise<FeedItem[]> {
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; seo-news-bot/1.0)" },
    });
    const xml = await res.text();
    return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/gi)].map((m) => {
      const block = m[1];
      return {
        title: xmlTag(block, "title"),
        link: xmlTag(block, "link").trim(),
        description: xmlTag(block, "description").replace(/<[^>]+>/g, "").slice(0, 400),
        pubDate: new Date(xmlTag(block, "pubDate") || Date.now()),
      };
    });
  } catch (e) {
    console.error("feed fetch failed", url, e);
    return [];
  }
}

async function fetchOgImage(pageUrl: string): Promise<string | null> {
  try {
    const res = await fetch(pageUrl, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; seo-news-bot/1.0)" },
    });
    const html = await res.text();
    const m =
      html.match(/<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i) ||
      html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']/i);
    return m ? m[1] : null;
  } catch (e) {
    console.error("og:image fetch failed", pageUrl, e);
    return null;
  }
}

async function translate(text: string): Promise<string> {
  if (!text.trim()) return "";
  try {
    const chunks: string[] = [];
    for (let i = 0; i < text.length; i += 450) chunks.push(text.slice(i, i + 450));
    const out: string[] = [];
    for (const chunk of chunks) {
      const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(chunk)}&langpair=en|fa`;
      const res = await fetch(url);
      const data = await res.json();
      out.push(data?.responseData?.translatedText ?? chunk);
    }
    return out.join(" ");
  } catch (e) {
    console.error("translate failed", e);
    return text;
  }
}

function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?؟])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 8);
}

function sourceLabel(link: string): string {
  if (link.includes("seroundtable")) return "SERoundtable";
  if (link.includes("searchenginejournal")) return "SEJ";
  if (link.includes("searchengineland")) return "SEL";
  return "منبع خارجی";
}

// Telegram caption limit is 1024 chars. Keep it short by design;
// this is just a safety net that drops the second bullet if needed.
function fitCaption(lines: string[], max = 1000): string {
  let text = lines.join("\n");
  if (text.length <= max) return text;
  const withoutSecondBullet = lines.filter((_, i) => i !== 2);
  text = withoutSecondBullet.join("\n");
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + "…";
}

async function buildPersianPost(item: FeedItem): Promise<string> {
  const [faTitle, faDesc] = await Promise.all([
    translate(item.title),
    translate(item.description),
  ]);

  const bulletSentences = splitSentences(faDesc).slice(0, 2);
  const bulletPrefix = "◆ ";
  const bullets = bulletSentences.length
    ? bulletSentences.map((s) => bulletPrefix + s)
    : [bulletPrefix + (faDesc || faTitle)];

  const redCircle = "🔴";
  const bulb = "💡";
  const pin = "📎";

  const lines = [
    `${redCircle} ${faTitle}`,
    "",
    ...bullets,
    "",
    `${bulb} اگه روی سئو یا مدیریت سایتکار می‌کنی، اینو چک کن.`,
    `${pin} <a href="${item.link}">منبع (${sourceLabel(item.link)})</a>  #سئو #اخبار_سئو`,
  ].map(rtl);

  return fitCaption(lines);
}

Deno.serve(async (req: Request) => {
  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const expectedSecret = await supabase
      .rpc("get_app_secret", { secret_name: "cron_shared_secret" })
      .then((r) => r.data as string | null);
    const gotSecret = req.headers.get("x-webhook-secret");
    if (!expectedSecret || gotSecret !== expectedSecret) {
      return new Response("unauthorized", { status: 401 });
    }

    const [botTokenRes, chatIdRes] = await Promise.all([
      supabase.rpc("get_app_secret", { secret_name: "telegram_bot_token" }),
      supabase.rpc("get_app_secret", { secret_name: "telegram_chat_id" }),
    ]);

    const botToken = botTokenRes.data as string | null;
    const chatId = chatIdRes.data as string | null;

    if (!botToken || !chatId) {
      return new Response("missing telegram secrets", { status: 500 });
    }

    const startOfDay = new Date();
    startOfDay.setHours(0, 0, 0, 0);
    const { count } = await supabase
      .from("posted_news")
      .select("*", { count: "exact", head: true })
      .gte("posted_at", startOfDay.toISOString());

    if ((count ?? 0) >= 17) {
      return new Response("daily cap reached", { status: 200 });
    }

    const allItems = (await Promise.all(FEEDS.map(fetchFeedItems))).flat();
    allItems.sort((a, b) => b.pubDate.getTime() - a.pubDate.getTime());

    const { data: postedRows } = await supabase.from("posted_news").select("source_url");
    const postedSet = new Set((postedRows ?? []).map((r: { source_url: string }) => r.source_url));

    const fresh = allItems.find((it) => it.link && !postedSet.has(it.link));

    if (!fresh) {
      return new Response("no new item", { status: 200 });
    }

    const caption = await buildPersianPost(fresh);
    const ogImage = await fetchOgImage(fresh.link);

    const tgBase = `https://api.telegram.org/bot${botToken}`;
    let tgRes: Response;

    if (ogImage) {
      tgRes = await fetch(`${tgBase}/sendPhoto`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, photo: ogImage, caption, parse_mode: "HTML" }),
      });
      if (!tgRes.ok) {
        console.error("sendPhoto failed, falling back to text-only", await tgRes.text());
        tgRes = await fetch(`${tgBase}/sendMessage`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ chat_id: chatId, text: caption, parse_mode: "HTML" }),
        });
      }
    } else {
      tgRes = await fetch(`${tgBase}/sendMessage`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text: caption, parse_mode: "HTML" }),
      });
    }

    if (!tgRes.ok) {
      const errText = await tgRes.text();
      console.error("telegram send failed", errText);
      return new Response(`telegram error: ${errText}`, { status: 500 });
    }

    await supabase.from("posted_news").insert({ source_url: fresh.link, title: fresh.title });

    return new Response("posted: " + fresh.title, { status: 200 });
  } catch (e) {
    console.error(e);
    return new Response(`error: ${e}`, { status: 500 });
  }
});
