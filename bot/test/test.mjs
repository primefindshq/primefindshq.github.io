// Offline test: runs the real Worker against fake Instagram webhooks.
// Instagram API calls are captured instead of sent. Run: npm test
import { readFileSync } from "node:fs";
import { createHmac } from "node:crypto";
import assert from "node:assert/strict";

const root = new URL("../../", import.meta.url);
const videos = JSON.parse(readFileSync(new URL("data/videos.json", root), "utf8"));

const sent = [];
globalThis.fetch = async (url, opts = {}) => {
  url = String(url);
  if (url.includes("videos.json")) return Response.json(videos);
  if (url.includes("?fields=caption")) {
    const caption = url.includes("/MEDIA_VILON") ? "שבת בבוקר 😴 (vilon)" : "סרטון בלי מילת קוד";
    return Response.json({ caption });
  }
  if (url.includes("graph.instagram.com")) {
    const body = JSON.parse(opts.body || "{}");
    if (body.recipient?.comment_id === "C_CLOSED") return new Response('{"error":"cannot message"}', { status: 400 });
    sent.push({ url, body });
    return Response.json({ ok: true });
  }
  throw new Error("unexpected fetch " + url);
};

const { default: worker } = await import("../src/worker.js");
const env = { IG_USER_ID: "ME", APP_SECRET: "s3cret", VERIFY_TOKEN: "vt", IG_ACCESS_TOKEN: "tok", MEDIA_MAP: "{}" };

async function post(payload, secret = env.APP_SECRET) {
  const raw = JSON.stringify(payload);
  const sig = "sha256=" + createHmac("sha256", secret).update(raw).digest("hex");
  const jobs = [];
  const res = await worker.fetch(
    new Request("https://bot/webhook", { method: "POST", body: raw, headers: { "x-hub-signature-256": sig } }),
    env,
    { waitUntil: (p) => jobs.push(p) },
  );
  await Promise.all(jobs);
  return res;
}
const comment = (id, text, { media = "MEDIA_VILON", from = "U" + id, parent } = {}) => ({
  object: "instagram",
  entry: [{ id: "ME", changes: [{ field: "comments", value: { id, text, from: { id: from, username: "x" }, media: { id: media }, ...(parent ? { parent_id: parent } : {}) } }] }],
});
const take = () => sent.splice(0);
let n = 0;
const ok = (name) => console.log(`  ✓ ${name}`) || n++;

// 1. Meta verification handshake
let r = await worker.fetch(new Request("https://bot/webhook?hub.mode=subscribe&hub.verify_token=vt&hub.challenge=123"), env, {});
assert.equal(await r.text(), "123");
r = await worker.fetch(new Request("https://bot/webhook?hub.mode=subscribe&hub.verify_token=WRONG&hub.challenge=1"), env, {});
assert.equal(r.status, 403);
ok("webhook verification (right/wrong token)");

// 2. forged signature is rejected and nothing is sent
r = await post(comment("C0", "קישור"), "not-the-secret");
assert.equal(r.status, 401);
assert.equal(take().length, 0);
ok("forged signature rejected");

// 3. any comment on the reel ("🔥", "וואו", "קישור") -> DM with /v/vilon/ + public reply
for (const [id, text] of [["C1", "🔥🔥"], ["C2", "וואו"], ["C3", "קישור בבקשה"]]) {
  await post(comment(id, text));
  const out = take();
  assert.equal(out.length, 2, `comment ${text}`);
  assert.equal(out[0].body.recipient.comment_id, id);
  assert.match(out[0].body.message.text, /\/v\/vilon\/\?utm_source=instagram/);
  assert.match(out[1].url, new RegExp(`${id}/replies$`));
}
ok("every comment on the reel (🔥 / וואו / קישור) -> DM with the video page + public reply");

// 4. a reply to someone else's comment -> nothing
await post(comment("C4", "חחחח איזה תגובה מצחיקה", { parent: "C2" }));
assert.equal(take().length, 0);
ok("reply to another comment ignored");

// 5. our own comment (including the bot's public replies) -> nothing
await post(comment("C5", "שלחנו לך בפרטי 📩", { from: "ME" }));
assert.equal(take().length, 0);
ok("own comments ignored (no loop)");

// 6. Meta sends the same event twice -> answered once
await post(comment("C3", "קישור בבקשה"));
assert.equal(take().length, 0);
ok("duplicate webhook ignored");

// 7. same person comments again on the same reel -> no second DM; on another reel -> yes
await post(comment("C6", "עוד תגובה", { from: "UC1" }));
assert.equal(take().length, 0);
await post(comment("C7", "גם פה", { from: "UC1", media: "MEDIA_OTHER" }));
assert.equal(take().length, 2);
ok("once per person per reel");

// 8. reel without a code word -> DM with the list of all videos
await post(comment("C8", "מגניב", { media: "MEDIA_OTHER" }));
assert.match(take()[0].body.message.text, /\/v\/\?utm_source/);
ok("reel without code word -> list of all videos");

// 9. DMs closed -> public "link in bio" reply instead
await post(comment("C_CLOSED", "לינק"));
let out = take();
assert.equal(out.length, 1);
assert.match(out[0].body.message, /ביו/);
ok("private reply fails -> public 'link in bio'");

// 10. incoming DMs are never answered
await post({ object: "instagram", entry: [{ id: "ME", messaging: [{ sender: { id: "U9" }, recipient: { id: "ME" }, message: { mid: "M1", text: "קישור?" } }] }] });
assert.equal(take().length, 0);
ok("DMs are not touched");

// 11. replies vary (anti-spam)
const seen = new Set();
for (let i = 0; i < 40; i++) {
  await post(comment("V" + i, "🔥", { from: "VAR" + i }));
  for (const s of take()) seen.add(s.body.message?.text || s.body.message);
}
assert.ok(seen.size >= 8, `only ${seen.size} different texts`);
ok(`replies vary: ${seen.size} different texts in 40 comments`);

console.log(`\nall ${n} checks passed`);
