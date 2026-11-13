// Cloudflare Worker: Instagram comment bot for "שודדים את אמזון".
//
// Every comment written directly on a reel gets a private DM with the link to the
// video's page, plus a short public reply. Replies to other comments are ignored,
// and the bot never touches the inbox (it doesn't read or answer DMs).
//
//  GET  /webhook   Meta's verification handshake
//  POST /webhook   comment events from Instagram (signature checked)
//  GET  /try       preview of the DM + public reply for the newest video
//  GET  /          health check
//
// Secrets (wrangler secret put ...): IG_ACCESS_TOKEN, APP_SECRET, VERIFY_TOKEN
// Vars (wrangler.toml): IG_USER_ID, GRAPH_VERSION, MEDIA_MAP (optional JSON)
// Optional KV binding: BOT_KV (dedup, once-per-person-per-video, token auto-refresh)

import { decideComment, findVideoInText } from "./logic.js";

const VIDEOS_URL = "https://raw.githubusercontent.com/primefindshq/primefindshq.github.io/main/data/videos.json";
const CACHE_MS = 5 * 60 * 1000;

// ---------- small in-memory caches (per Worker instance) ----------
const mem = { videos: null, seen: new Map(), captions: new Map() };

async function loadVideos() {
  if (mem.videos && Date.now() - mem.videos.at < CACHE_MS) return mem.videos.value;
  try {
    const r = await fetch(VIDEOS_URL, { cf: { cacheTtl: 300 } });
    if (!r.ok) throw new Error(`${r.status}`);
    mem.videos = { at: Date.now(), value: await r.json() };
  } catch (e) {
    console.log("loading videos failed", String(e));
    if (!mem.videos) return [];
  }
  return mem.videos.value;
}

// ---------- KV helpers (everything still works without KV) ----------
async function seenBefore(env, key, ttlSec) {
  if (mem.seen.has(key)) return true;
  mem.seen.set(key, Date.now());
  if (mem.seen.size > 5000) mem.seen.clear();
  if (!env.BOT_KV) return false;
  if (await env.BOT_KV.get(key)) return true;
  await env.BOT_KV.put(key, "1", { expirationTtl: ttlSec });
  return false;
}

async function getToken(env) {
  if (env.BOT_KV) {
    const t = await env.BOT_KV.get("ig_token");
    if (t) return t;
  }
  return env.IG_ACCESS_TOKEN;
}

// ---------- Instagram Graph API ----------
function graph(env, path) {
  return `https://graph.instagram.com/${env.GRAPH_VERSION || "v23.0"}/${path}`;
}

async function igPost(env, path, body) {
  const r = await fetch(graph(env, path), {
    method: "POST",
    headers: { Authorization: `Bearer ${await getToken(env)}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const txt = await r.text();
  if (!r.ok) throw new Error(`IG ${path} ${r.status}: ${txt.slice(0, 300)}`);
  return txt;
}

// "Private reply": a DM tied to a comment. Instagram allows one per comment, within 7 days.
const sendPrivateReply = (env, commentId, text) =>
  igPost(env, `${env.IG_USER_ID}/messages`, { recipient: { comment_id: commentId }, message: { text } });

const replyToComment = (env, commentId, message) => igPost(env, `${commentId}/replies`, { message });

async function videoForMedia(env, mediaId, videos) {
  // 1) explicit map in wrangler.toml: MEDIA_MAP = '{"1789...": "vilon"}'
  try {
    const map = env.MEDIA_MAP ? JSON.parse(env.MEDIA_MAP) : {};
    if (map[mediaId]) return videos.find((v) => v.slug === map[mediaId]) || null;
  } catch {}
  // 2) the caption mentions the code word, e.g. "(vilon)" or ".../v/vilon"
  let caption = mem.captions.get(mediaId);
  if (caption === undefined) {
    try {
      const r = await fetch(graph(env, `${mediaId}?fields=caption`), {
        headers: { Authorization: `Bearer ${await getToken(env)}` },
      });
      caption = r.ok ? (await r.json()).caption || "" : "";
    } catch {
      caption = "";
    }
    mem.captions.set(mediaId, caption);
  }
  return findVideoInText(caption, videos);
}

// ---------- the one thing the bot does ----------
async function handleComment(env, value) {
  // cheap checks first (own comment / reply to a comment) before any network call
  if (!decideComment({ comment: value, video: null, videos: [], myId: env.IG_USER_ID })) return;
  if (await seenBefore(env, `c:${value.id}`, 8 * 86400)) return; // Meta sometimes sends the same event twice

  // someone who comments 5 times on the same reel gets the link once, not 5 DMs
  const person = value.from?.id || value.from?.username;
  const mediaId = value.media?.id || "unknown";
  if (person && (await seenBefore(env, `u:${person}:${mediaId}`, 30 * 86400))) return;

  const videos = await loadVideos();
  const video = value.media?.id ? await videoForMedia(env, value.media.id, videos) : null;
  const plan = decideComment({ comment: value, video, videos, myId: env.IG_USER_ID });
  if (!plan) return;

  try {
    await sendPrivateReply(env, value.id, plan.dm);
    await replyToComment(env, value.id, plan.publicReply);
    console.log("comment answered", value.id, video?.slug || "(no code word)");
  } catch (e) {
    console.log("private reply failed, replying publicly", String(e));
    await replyToComment(env, value.id, plan.fallbackPublicReply).catch((e2) => console.log(String(e2)));
  }
}

async function handleWebhook(env, payload) {
  for (const entry of payload.entry || []) {
    for (const ch of entry.changes || []) {
      if (ch.field === "comments") {
        await handleComment(env, ch.value || {}).catch((e) => console.log("comment error", String(e)));
      }
    }
    // entry.messaging (DMs) is deliberately ignored: the inbox is handled by a human.
  }
}

// ---------- security: Meta signs every POST with the app secret ----------
async function validSignature(env, raw, header) {
  if (!env.APP_SECRET || !header?.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.APP_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw)));
  const hex = [...sig].map((b) => b.toString(16).padStart(2, "0")).join("");
  const given = header.slice(7);
  if (given.length !== hex.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) diff |= hex.charCodeAt(i) ^ given.charCodeAt(i);
  return diff === 0;
}

// ---------- long-lived tokens expire after 60 days: refresh weekly (needs KV) ----------
async function refreshToken(env) {
  if (!env.BOT_KV) return console.log("no BOT_KV: token refresh skipped");
  const current = await getToken(env);
  const r = await fetch(`https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=${encodeURIComponent(current)}`);
  const j = await r.json().catch(() => ({}));
  if (j.access_token) {
    await env.BOT_KV.put("ig_token", j.access_token);
    console.log("token refreshed, expires in", j.expires_in);
  } else console.log("token refresh failed", JSON.stringify(j).slice(0, 200));
}

// Called on webhook traffic: refresh when the last refresh is over 7 days old.
async function maybeRefreshToken(env) {
  if (!env.BOT_KV) return;
  const last = Number((await env.BOT_KV.get("ig_token_refreshed_at")) || 0);
  if (Date.now() - last < 7 * 86400 * 1000) return;
  await env.BOT_KV.put("ig_token_refreshed_at", String(Date.now()));
  await refreshToken(env).catch((e) => console.log("refresh error", String(e)));
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj, null, 2), { status, headers: { "content-type": "application/json; charset=utf-8" } });

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook" && request.method === "GET") {
      const ok = url.searchParams.get("hub.mode") === "subscribe" && url.searchParams.get("hub.verify_token") === env.VERIFY_TOKEN;
      return ok ? new Response(url.searchParams.get("hub.challenge")) : new Response("forbidden", { status: 403 });
    }

    if (url.pathname === "/webhook" && request.method === "POST") {
      const raw = await request.text();
      if (!(await validSignature(env, raw, request.headers.get("x-hub-signature-256")))) {
        return new Response("bad signature", { status: 401 });
      }
      let payload;
      try {
        payload = JSON.parse(raw);
      } catch {
        return new Response("bad json", { status: 400 });
      }
      ctx.waitUntil(handleWebhook(env, payload)); // answer Meta fast, work in the background
      ctx.waitUntil(maybeRefreshToken(env));
      return new Response("EVENT_RECEIVED");
    }

    if (url.pathname === "/try") {
      const videos = await loadVideos();
      const example = { id: "example", text: "🔥", from: { id: "someone" } };
      return json({ newestVideo: videos[0]?.slug, wouldSend: decideComment({ comment: example, video: videos[0], videos, myId: env.IG_USER_ID }) });
    }

    if (url.pathname === "/") return new Response("שודדים את אמזון bot: ok");
    return new Response("not found", { status: 404 });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(refreshToken(env));
  },
};
