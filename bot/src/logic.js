// The bot's "brain": decides what to send to someone who commented on a reel.
// No network calls here, so it's easy to test (see test/test.mjs).

import { T, pick } from "./texts.js";

export const SITE = "https://primefindshq.github.io";

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function withUtm(url, medium) {
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}utm_source=instagram&utm_medium=${medium}`;
}

export function videoUrl(slug) {
  return `${SITE}/v/${slug}/`;
}

// Find which video a caption talks about.
// Matches "/v/<slug>" or the slug as a separate Latin word, e.g. "(vilon)".
export function findVideoInText(text, videos) {
  const low = String(text || "").toLowerCase();
  for (const v of videos) {
    const s = v.slug.toLowerCase();
    if (low.includes(`/v/${s}`)) return v;
    if (new RegExp(`(^|[^a-z0-9-])${escapeRe(s)}($|[^a-z0-9-])`).test(low)) return v;
  }
  return null;
}

/**
 * Should we answer this comment, and with what?
 * Rule: every comment written directly on the reel gets a DM with the link.
 * Replies to other comments (parent_id) and our own comments are skipped.
 * @returns null (do nothing) or { dm, publicReply, fallbackPublicReply }
 */
export function decideComment({ comment, video, videos, myId }) {
  if (!comment || !comment.id) return null;
  if (comment.from?.id && comment.from.id === myId) return null; // never answer ourselves
  if (comment.parent_id) return null; // a reply to someone else's comment

  let dm;
  if (video) {
    dm = pick(T.dmVideo)
      .replace("{title}", video.title)
      .replace("{url}", withUtm(videoUrl(video.slug), "dm"));
  } else {
    const newest = videos[0];
    dm = pick(T.dmGeneric)
      .replace("{index}", withUtm(`${SITE}/v/`, "dm"))
      .replace("{newestTitle}", newest ? newest.title : "")
      .replace("{newestUrl}", newest ? withUtm(videoUrl(newest.slug), "dm") : `${SITE}/v/`);
  }
  return {
    dm,
    publicReply: pick(T.publicReplySent),
    fallbackPublicReply: pick(T.publicReplyBio),
  };
}
