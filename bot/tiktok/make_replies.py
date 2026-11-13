"""Builds bot/tiktok/replies.html: ready-made Hebrew replies for TikTok comments,
one card per video with copy buttons. TikTok has no public API for comments/DMs,
so you paste these yourself (a copy takes one tap).

The file is written as an Artifact page (no <html>/<body> wrapper) so it can be
published to claude.ai and opened on the phone; it also opens fine in a desktop browser.

Run after adding a video:   py bot/tiktok/make_replies.py
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "replies.html")

# Links in TikTok comments aren't clickable and can get a comment hidden,
# so the replies send people to the bio instead.
VIDEO_REPLIES = [
    "הקישור בביו 🔗 שם \"{title}\" מופיע בראש הרשימה",
    "בביו! לוחצים על הקישור ומוצאים את הסרטון הזה 👆",
    "יש קישור בביו 🙌 הסרטון הזה מחכה שם",
    "הכל בקישור שבביו 👆 מחפשים \"{short}\"",
]
GENERIC = [
    ("מחיר", "המחיר מופיע בעמוד של הסרטון, קישור בביו 👆 (בדולרים, לפני משלוח)"),
    ("משלוח לישראל", "רוב המוצרים נשלחים לישראל, אבל כדאי לבדוק בעמוד באמזון לפני הזמנה 🙏"),
    ("תודה / מחמאה", "תודה! 🙌 עוד מציאות בדרך"),
    ("מה זה?", "הפרטים בקישור שבביו 👆"),
    ("עובד?", "לא בדקנו בעצמנו, אבל אפשר לקרוא את הביקורות באמזון דרך הקישור בביו 👆"),
]


def esc(s):
    return html.escape(s, quote=True)


def main():
    with open(os.path.join(ROOT, "data", "videos.json"), encoding="utf-8") as f:
        videos = json.load(f)
    custom = {}
    custom_path = os.path.join(HERE, "custom_replies.json")
    if os.path.exists(custom_path):
        with open(custom_path, encoding="utf-8") as f:
            custom = json.load(f)

    cards = []
    for v in videos:
        title = v["title"]
        short = title.split(":")[-1].strip()
        replies = list(custom.get(v["slug"], [])) + [r.format(title=title, short=short) for r in VIDEO_REPLIES]
        btns = "".join(f'<button type="button" class="r" data-t="{esc(r)}">{esc(r)}</button>' for r in replies)
        cards.append(
            f'<section class="card" data-s="{esc(title.lower() + " " + v["slug"])}">'
            f'<h2>{esc(title)}</h2>'
            f'<p class="meta"><span class="code">{esc(v["slug"])}</span> · {esc(v.get("date", ""))}</p>'
            f'<div class="list">{btns}</div></section>'
        )
    generic = "".join(
        f'<button type="button" class="r" data-t="{esc(t)}"><b>{esc(k)}</b>{esc(t)}</button>' for k, t in GENERIC
    )

    page = f"""<title>תשובות טיקטוק</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800&display=swap">
<style>
/* layout: one narrow column of tap targets, thumb-sized, search pinned on top */
:root {{
  --bg: #f3f2f6; --surface: #ffffff; --ink: #18161d; --muted: #67636f; --line: #dfdce5;
  --accent: #d6204f; --on-accent: #ffffff;
  --font: "Heebo", "Segoe UI", Arial, sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #121116; --surface: #1c1a22; --ink: #f0eef4; --muted: #a29eab; --line: #322f3a;
  --accent: #ff4d79; --on-accent: #16050b; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #121116; --surface: #1c1a22; --ink: #f0eef4; --muted: #a29eab; --line: #322f3a;
  --accent: #ff4d79; --on-accent: #16050b; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font: 16px/1.5 var(--font); }}
.wrap {{ max-width: 640px; margin: 0 auto; padding-block: 20px 40px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 14px; }}
h1 {{ font-size: 1.6rem; font-weight: 800; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }}
.sub {{ color: var(--muted); margin: 0; max-width: 60ch; }}
.search {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--bg); padding-block: 6px; }}
body::before {{ content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--bg); }}
#q {{ width: 100%; padding: 12px 14px; font: inherit; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); color: var(--ink); }}
#q:focus-visible, .r:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 14px; min-width: 0; }}
.card.generic {{ border-color: var(--accent); }}
h2 {{ font-size: 1.05rem; font-weight: 700; margin: 0; text-wrap: balance; }}
.meta {{ color: var(--muted); font-size: 0.82rem; margin: 2px 0 10px; }}
.code {{ font-family: ui-monospace, Consolas, monospace; direction: ltr; unicode-bidi: isolate; }}
.list {{ display: flex; flex-direction: column; gap: 8px; }}
.r {{ display: block; width: 100%; text-align: start; font: inherit; color: inherit; background: var(--bg);
  border: 1px solid var(--line); border-radius: 10px; padding: 11px 12px; cursor: pointer; min-height: 48px;
  transition: background .15s, border-color .15s; }}
.r b {{ display: block; font-size: 0.8rem; color: var(--accent); font-weight: 700; }}
.r:hover {{ border-color: var(--accent); }}
.r.ok {{ background: var(--accent); color: var(--on-accent); border-color: var(--accent); }}
.r.ok b {{ color: var(--on-accent); }}
.empty {{ color: var(--muted); text-align: center; }}
@media (prefers-reduced-motion: reduce) {{ .r {{ transition: none; }} }}
</style>
<div class="wrap" dir="rtl" lang="he">
  <h1>תשובות מוכנות לטיקטוק</h1>
  <p class="sub">לוחצים על תשובה, היא מועתקת, ומדביקים בטיקטוק. כדאי לגוון ולא להדביק את אותה תשובה שוב ושוב.</p>
  <div class="search"><input id="q" type="search" placeholder="חיפוש סרטון…" autocomplete="off" aria-label="חיפוש סרטון"></div>
  <section class="card generic"><h2>תשובות כלליות</h2><p class="meta">מתאימות לכל סרטון</p><div class="list">{generic}</div></section>
  {''.join(cards)}
  <p class="empty" id="none" hidden>לא נמצא סרטון כזה</p>
</div>
<script>
function flash(b) {{ b.classList.add('ok'); setTimeout(function () {{ b.classList.remove('ok'); }}, 900); }}
function fallbackCopy(text) {{
  var t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', '');
  t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
  try {{ document.execCommand('copy'); }} catch (e) {{}} t.remove();
}}
document.addEventListener('click', function (e) {{
  var b = e.target.closest('.r'); if (!b) return;
  var text = b.dataset.t;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text).then(function () {{ flash(b); }}, function () {{ fallbackCopy(text); flash(b); }});
  }} else {{ fallbackCopy(text); flash(b); }}
}});
document.getElementById('q').addEventListener('input', function (e) {{
  var q = e.target.value.trim().toLowerCase(), shown = 0;
  document.querySelectorAll('.card[data-s]').forEach(function (c) {{
    var ok = !q || c.dataset.s.indexOf(q) !== -1; c.hidden = !ok; if (ok) shown++;
  }});
  document.getElementById('none').hidden = shown > 0;
}});
</script>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(videos)} videos)")


if __name__ == "__main__":
    main()
