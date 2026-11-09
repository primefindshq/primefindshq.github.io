"""
PRIME.FINDS static site generator.

Stands in for what a Next.js `generateStaticParams` + `generateMetadata`
build step would do, without requiring Node.js on this machine. Reads the
"database" (data/*.json) and renders:

  - public/index.html                          (homepage)
  - public/category/<slug>/index.html          (one per category)
  - public/product/<slug>/index.html           (one per PUBLISHED product)
  - public/about.html, affiliate-disclosure.html, privacy-policy.html,
    terms.html, accessibility.html, cookie-notice.html, 404.html
  - public/data/products.json, categories.json (client-side data snapshot)
  - public/sitemap.xml, robots.txt, site.webmanifest

Run via: python scripts/build.py   (or: py scripts/build.py on Windows)

This is intentionally a thin, dependency-free script (stdlib only) so it's
easy to read end to end. When this project migrates to Next.js, each
`render_*` function below maps almost 1:1 onto a React page/layout
component, and data/*.json becomes the seed for a real database.
"""
import html
import json
import math
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
PUBLIC_DIR = os.path.join(ROOT, "public")

CSS_FILES = [
    "/css/tokens.css",
    "/css/base.css",
    "/css/layout.css",
    "/css/components.css",
    "/css/animations.css",
    "/css/pages.css",
    "/css/a11y.css",
]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def render_analytics_head(site):
    """Cookieless Umami analytics, switched on by "analytics": {"umami": "<website id>"}
    in site-config.json. data-domains keeps local previews out of the numbers."""
    website_id = (site.get("analytics") or {}).get("umami")
    if not website_id:
        return ""
    host = site["url"].split("//", 1)[-1].strip("/")
    return ('<script>window.__PRIME_FINDS_ANALYTICS_CONFIG={provider:"umami"};</script>'
            f'<script defer src="https://cloud.umami.is/script.js" data-website-id="{esc(website_id)}" data-domains="{esc(host)}"></script>')


def load_data():
    with open(os.path.join(DATA_DIR, "site-config.json"), encoding="utf-8") as f:
        site = json.load(f)
    with open(os.path.join(DATA_DIR, "categories.json"), encoding="utf-8") as f:
        categories = json.load(f)
    with open(os.path.join(DATA_DIR, "products.json"), encoding="utf-8") as f:
        products = json.load(f)
    return site, categories, products


def load_collections(published):
    """Curated collections (data/collections.json). Each lists product slugs; slugs that are
    not published are skipped, and a collection with fewer than 3 live products is dropped."""
    path = os.path.join(DATA_DIR, "collections.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    by_slug = {p["slug"]: p for p in published}
    out = []
    for c in raw:
        items = [by_slug[s] for s in c["products"] if s in by_slug]
        if len(items) >= 3:
            out.append({**c, "items": items})
    return out


def load_videos(published):
    """Video landing pages (data/videos.json), newest first. Each lists the products
    a video shows, under the same numbers the video uses; unpublished slugs are skipped."""
    path = os.path.join(DATA_DIR, "videos.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    by_slug = {p["slug"]: p for p in published}
    out = []
    for v in raw:
        items = [{**i, "product": by_slug[i["slug"]]} for i in v["items"] if i["slug"] in by_slug]
        if items:
            out.append({**v, "items": sorted(items, key=lambda i: i["n"])})
    return out


def load_guides(published):
    """Gift guides (data/guides.json): an editorial intro, an ordered list of product slugs
    and a short FAQ. Unpublished slugs are skipped; a guide with fewer than 5 live picks is dropped."""
    path = os.path.join(DATA_DIR, "guides.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    by_slug = {p["slug"]: p for p in published if p.get("availability") != "unavailable"}
    out = []
    for g in raw:
        items = [by_slug[s] for s in g["items"] if s in by_slug]
        if len(items) >= 5:
            out.append({**g, "items": items})
    return out


def related_products(product, published, limit=4):
    """Products most like this one: same subcategory, same category, shared secondary categories
    and shared tags all add to the score (never the product itself); ties fall back to newest."""
    def own_tags(p):
        return {t.lower() for t in p.get("tags", []) if t.lower() != "gift"}
    cats = {product["category"], *product.get("secondaryCategories", [])}
    tags = own_tags(product)
    scored = []
    for p in published:
        if p["slug"] == product["slug"]:
            continue
        score = 0
        if product.get("subcategory") and p.get("subcategory") == product["subcategory"]:
            score += 3
        if p["category"] == product["category"]:
            score += 2
        score += len(cats & {p["category"], *p.get("secondaryCategories", [])})
        score += 2 * len(tags & own_tags(p))
        scored.append((score, p["id"], p))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [p for _, _, p in scored[:limit]]


# --------------------------------------------------------------------------
# Small formatting helpers (mirrors of js/core/utils.js, server-side)
# --------------------------------------------------------------------------

def esc(value):
    return html.escape(str(value), quote=True)


def format_price(price, currency="USD"):
    if price is None:
        return "לבדיקת מחיר"
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency, currency + " ")
    return f"{symbol}{price:,.2f}"


def render_stars(rating, review_count=None):
    rating = rating or 0
    full = round(rating)
    stars = ""
    for i in range(5):
        filled = i < full
        stars += (
            f'<svg viewBox="0 0 20 20" width="13" height="13" fill="{"currentColor" if filled else "none"}" '
            f'stroke="currentColor" stroke-width="1.2" aria-hidden="true">'
            f'<path d="M10 1.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>'
        )
    if rating > 0:
        label = f"{rating:.1f} מתוך 5" + (f" ({review_count:,} ביקורות)" if review_count else "")
        extra = f'<span>{rating:.1f}</span>'
        if review_count:
            extra += f'<span class="text-faint">({review_count:,})</span>'
    else:
        label = "עדיין ללא דירוג"
        extra = '<span class="text-faint">חדש</span>'
    return f'<span class="rating" role="img" aria-label="{esc(label)}"><span class="stars">{stars}</span>{extra}</span>'


def category_label(slug):
    for c in _ALL_CATEGORIES or []:
        if c["slug"] == slug:
            return c["name"]
    return slug.replace("-", " ")


_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי",
           "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]


def format_date_long(iso):
    """'2026-09-20' -> '20 September 2026' (unambiguous for an international audience)."""
    y, m, d = (int(part) for part in iso.split("-"))
    return f"{d} ב{_MONTHS[m - 1]} {y}"


def render_breadcrumbs(items):
    """items: [(label, href_or_None), ...]; the last one is the current page.
    Separators are decorative, so they are hidden from assistive technology."""
    parts = []
    for i, (label, href) in enumerate(items):
        last = i == len(items) - 1
        if last:
            parts.append(f'<span aria-current="page">{esc(label)}</span>')
        else:
            parts.append(f'<a href="{href}">{esc(label)}</a><span class="sep" aria-hidden="true">/</span>')
    return f'<nav class="breadcrumbs" aria-label="מיקום באתר">{"".join(parts)}</nav>'


def render_contact_paragraph(site, lead=""):
    """The one place that decides how a visitor can reach PRIME.FINDS. Only channels
    that actually exist are offered: an email address if one has been configured in
    data/site-config.json, and the public issue tracker of the site's repository."""
    contact = site.get("contact", {})
    email = contact.get("email", "").strip()
    issues = contact.get("issuesUrl", "").strip()
    bits = []
    if email:
        bits.append(f'במייל <a href="mailto:{esc(email)}">{esc(email)}</a>')
    if issues:
        bits.append(
            f'דרך <a href="{esc(issues)}" target="_blank" rel="noopener">מערכת הפניות הציבורית שלנו ב-GitHub</a> '
            f'(נדרש חשבון GitHub חינמי, ומה שנכתב שם גלוי לכולם, לכן אין לכלול פרטים אישיים)'
        )
    if not bits:
        return ""
    joined = " או ".join(bits)
    return f"<p>{lead}אפשר ליצור איתנו קשר {joined}.</p>"


def product_in_category(product, category_slug):
    """A product belongs to its primary category plus any listed secondaryCategories --
    lets one product (e.g. a candle warmer that's both home decor and a gift) surface
    in more than one category grid without duplicating the product entry."""
    return product["category"] == category_slug or category_slug in product.get("secondaryCategories", [])


# --------------------------------------------------------------------------
# Shared chrome: header, mobile menu, search overlay, footer
# --------------------------------------------------------------------------

SEARCH_ICON = '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="9" cy="9" r="6.5"/><path d="M18 18l-3.8-3.8"/></svg>'
CLOSE_ICON = '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg>'
INSTAGRAM_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1"/></svg>'
# The site is right-to-left, so "forward" points left.
CHEVRON_ICON = '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M13 5l-6 5 6 5"/></svg>'
CHEVRON_LEFT_ICON = '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 5l6 5-6 5"/></svg>'
A11Y_ICON = '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="8"/><circle cx="10" cy="5.9" r="1.1" fill="currentColor" stroke="none"/><path d="M5.6 8.3c3 .9 5.8.9 8.8 0M10 8.7v3.3M10 12l-2.1 3.5M10 12l2.1 3.5"/></svg>'

# Applies the visitor's saved accessibility choices (text size / high contrast /
# reduced motion) before first paint, so the page never flashes at the wrong size
# or contrast. The same keys are read and written by js/core/a11y.js.
A11Y_HEAD = (
    '<script>(function(){try{var s=JSON.parse(localStorage.getItem("pf-a11y")||"{}"),d=document.documentElement;'
    'if(s.text>0&&s.text<5){d.setAttribute("data-text",String(s.text|0));if(s.text>1)d.classList.add("text-large")}'
    'if(s.contrast)d.setAttribute("data-contrast","high");'
    'if(s.motion)d.setAttribute("data-motion","reduce")}catch(e){}})();</script>'
    '<noscript><style>[data-a11y-toggle]{display:none}</style></noscript>'
)


# Always-visible header links. The first one stays visible on phones as a pill; the
# rest show from tablet width up (the full menu stays behind "Index").
HEADER_NAV = [
    ("guides", "מדריכי מתנות", "/guides/"),
    ("videos", "סרטונים", "/v/"),
    ("under-25", "עד 25 דולר", "/category/under-25/"),
    ("categories", "קטגוריות", "/#categories"),
]


def render_header(site, active=None):
    header_links = "".join(
        f'<a class="header-nav__link" href="{href}" aria-current="page">{esc(label)}</a>' if active == key
        else f'<a class="header-nav__link" href="{href}">{esc(label)}</a>'
        for key, label, href in HEADER_NAV
    )
    return f"""
<a class="skip-link" href="#main-content">דילוג לתוכן הראשי</a>
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])}, דף הבית"><picture><source media="(max-width: 640px)" srcset="/assets/logo/wordmark-compact.png" width="972" height="371" /><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1676" height="168" /></picture></a>
    <nav class="header-nav" aria-label="ראשי">
      {header_links}
    </nav>
    <div class="header-actions">
      <button class="icon-btn" type="button" data-search-open aria-haspopup="dialog" aria-label="חיפוש מוצרים">{SEARCH_ICON}</button>
      <button class="icon-btn" type="button" data-a11y-toggle aria-haspopup="dialog" aria-expanded="false" aria-controls="a11y-panel" aria-label="אפשרויות נגישות">{A11Y_ICON}</button>
      <button class="index-trigger" type="button" data-index-toggle aria-expanded="false" aria-haspopup="dialog" aria-controls="site-index" aria-label="תפריט האתר">
        <span class="index-trigger__glyph" aria-hidden="true"><span></span><span></span></span>
        <span class="index-trigger__label">תפריט</span>
      </button>
    </div>
  </div>
</header>
"""


def render_site_index(site, categories, counts):
    nav_links = "".join(
        f'<li><a class="site-index__nav-link" href="{link["href"]}">{esc(link["label"])}</a></li>'
        for link in site["navLinks"]
    )
    cat_items = "".join(
        f'<a class="site-index__cat" href="/category/{c["slug"]}/">'
        f'<span class="site-index__cat-name">{esc(c["name"])}</span>'
        f'<span class="site-index__cat-count">{counts.get(c["slug"], 0):02d}</span></a>'
        for c in categories
    )
    legal_items = "".join(
        f'<li><a href="{l["href"]}">{esc(l["label"])}</a></li>' for l in site["footerLegalLinks"]
    )
    return f"""
<div class="site-index" id="site-index" data-index-panel role="dialog" aria-modal="true" aria-label="תפריט האתר">
  <div class="site-index__top">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])}, דף הבית"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1676" height="168" /></a>
    <button class="icon-btn" type="button" data-index-close aria-label="סגירת התפריט">{CLOSE_ICON}</button>
  </div>
  <div class="site-index__body">
    <nav aria-label="עמודים"><ul class="site-index__nav-list">{nav_links}</ul></nav>
    <nav aria-label="קטגוריות">
      <span class="eyebrow site-index__cats-label">הקטלוג</span>
      <div class="site-index__cats">{cat_items}</div>
    </nav>
  </div>
  <div class="site-index__footer">
    <p>{esc(site['tagline'])}</p>
    <nav aria-label="מידע משפטי ונגישות"><ul class="site-index__legal">{legal_items}</ul></nav>
  </div>
</div>
"""


def render_brand_intro():
    # Deterministic scatter of drifting dust points -- server-rendered so
    # there's no client-side randomness to cause a flash of layout, varied
    # just enough that the dozen dots don't read as one repeated sprite.
    dust = []
    positions = [
        (18, 70), (82, 65), (30, 25), (70, 20), (50, 82), (12, 40),
        (88, 45), (44, 12), (60, 88), (25, 55),
    ]
    for i, (x, y) in enumerate(positions):
        drift_x = 10 + (i % 5) * 4
        drift_y = -(50 + (i % 4) * 18)
        delay = (i % 6) * 380
        style = (
            f"left:{x}%; top:{y}%; animation-delay:{delay}ms; "
            f"--dust-x:{drift_x}px; --dust-y:{drift_y}px;"
        )
        dust.append(f'<span style="{style}"></span>')

    # The WebGL entrance draws into the canvas (js/components/introScene.js).
    # The CSS entrance -- the fallback when WebGL is unavailable -- lives in
    # the wrapper, inert unless brandIntro.js selects it. The still is the
    # reduced-motion entrance (opacity only).
    # The artwork is decorative and stays hidden from assistive technology; the two
    # controls (skip, and a route to the accessibility statement) are real, focusable
    # elements outside the hidden art, so the entrance can never be a barrier.
    return f"""
<div class="brand-intro" data-brand-intro role="group" aria-label="פתיח">
  <canvas class="brand-intro__canvas" aria-hidden="true"></canvas>
  <div class="brand-intro__still" aria-hidden="true"><img src="/assets/logo/wordmark.png" alt="" width="1075" height="580" /></div>
  <div class="brand-intro__css" aria-hidden="true">
    <div class="brand-intro__atmosphere">{"".join(dust)}</div>
    <div class="brand-intro__glow"></div>
    <div class="brand-intro__ring"></div>
    <div class="brand-intro__mark"><img src="/assets/logo/mark.png" alt="" width="374" height="419" /></div>
    <div class="brand-intro__word"><img src="/assets/logo/wordmark.png" alt="" width="1075" height="580" /></div>
    <div class="brand-intro__rule"></div>
  </div>
  <div class="brand-intro__tools">
    <button type="button" class="brand-intro__skip" data-intro-skip>דילוג על הפתיח</button>
    <a class="brand-intro__link" href="/accessibility.html">נגישות</a>
  </div>
</div>
"""


def render_search_overlay():
    return f"""
<div class="search-overlay" data-search-overlay role="dialog" aria-modal="true" aria-labelledby="search-overlay-title">
  <div class="search-overlay__panel">
    <h2 class="sr-only" id="search-overlay-title">חיפוש מוצרים</h2>
    <div class="search-overlay__input-row">
      {SEARCH_ICON}
      <input class="search-overlay__input" type="search" placeholder="חיפוש מוצרים וקטגוריות…" data-search-input aria-label="חיפוש מוצרים" autocomplete="off" enterkeyhint="search" spellcheck="false" />
      <button class="icon-btn" type="button" data-search-close aria-label="סגירת החיפוש">{CLOSE_ICON}</button>
    </div>
    <p class="sr-only" role="status" aria-live="polite" data-search-status></p>
    <div data-search-results></div>
  </div>
</div>
"""


def render_a11y_panel():
    """The accessibility options popover. Every control does something real:
    text size scales the whole site (rem-based type), high contrast swaps the
    colour tokens, reduce motion mirrors prefers-reduced-motion. Behaviour lives
    in js/components/a11yPanel.js + js/core/a11y.js; styling in css/a11y.css."""
    return f"""
<div class="a11y-panel" id="a11y-panel" data-a11y-panel role="dialog" aria-modal="true" aria-labelledby="a11y-panel-title" tabindex="-1">
  <div class="a11y-panel__head">
    <h2 class="a11y-panel__title" id="a11y-panel-title">אפשרויות נגישות</h2>
    <button class="icon-btn" type="button" data-a11y-close aria-label="סגירת אפשרויות הנגישות">{CLOSE_ICON}</button>
  </div>
  <div class="a11y-panel__body">
    <div class="a11y-row" role="group" aria-labelledby="a11y-text-label">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-text-label">גודל טקסט</span>
        <span class="a11y-row__hint">כרגע <span data-a11y-text-value>100%</span></span>
      </div>
      <div class="a11y-stepper">
        <button type="button" class="a11y-btn" data-a11y-text-down>הקטנת טקסט</button>
        <button type="button" class="a11y-btn" data-a11y-text-up>הגדלת טקסט</button>
      </div>
    </div>
    <div class="a11y-row">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-contrast-label">ניגודיות גבוהה</span>
        <span class="a11y-row__hint">טקסט, גבולות ומסגרות מיקוד חזקים יותר.</span>
      </div>
      <button type="button" class="a11y-switch" role="switch" aria-checked="false" aria-labelledby="a11y-contrast-label" data-a11y-contrast><span class="a11y-switch__knob" aria-hidden="true"></span></button>
    </div>
    <div class="a11y-row">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-motion-label">הפחתת תנועה</span>
        <span class="a11y-row__hint" data-a11y-motion-hint>מעברים רגועים יותר.</span>
      </div>
      <button type="button" class="a11y-switch" role="switch" aria-checked="false" aria-labelledby="a11y-motion-label" data-a11y-motion><span class="a11y-switch__knob" aria-hidden="true"></span></button>
    </div>
  </div>
  <div class="a11y-panel__foot">
    <button type="button" class="btn btn--secondary btn--sm" data-a11y-reset>איפוס הכול</button>
    <a class="a11y-panel__link" href="/accessibility.html">הצהרת נגישות</a>
  </div>
  <p class="sr-only" role="status" aria-live="polite" data-a11y-status></p>
</div>
"""


def render_footer(site):
    categories_links = "".join(
        f'<li><a href="/category/{c["slug"]}/">{esc(c["name"])}</a></li>' for c in _ALL_CATEGORIES
    )
    nav_links = "".join(f'<li><a href="{l["href"]}">{esc(l["label"])}</a></li>' for l in site["navLinks"])
    legal_links = "".join(f'<li><a href="{l["href"]}">{esc(l["label"])}</a></li>' for l in site["footerLegalLinks"])
    instagram = site["social"].get("instagram", "")
    # With no Instagram account configured the icon would be a control that does nothing
    # (and only explained itself in a hover tooltip), so it is left out of the
    # accessibility tree entirely rather than presented as a disabled control.
    social_html = (
        f'<a href="{esc(instagram)}" target="_blank" rel="noopener" aria-label="{esc(site['siteName'])} באינסטגרם (נפתח בלשונית חדשה)">{INSTAGRAM_ICON}</a>'
        if instagram
        else f'<span aria-hidden="true">{INSTAGRAM_ICON}</span>'
    )
    year = "2026"
    return f"""
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand-logo" href="/"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1676" height="168" /></a>
        <p class="footer-brand__tagline">{esc(site['tagline'])}</p>
      </div>
      <div>
        <h2 class="footer-heading">ניווט</h2>
        <ul class="footer-links">{nav_links}</ul>
      </div>
      <div>
        <h2 class="footer-heading">קטגוריות</h2>
        <ul class="footer-links">{categories_links}</ul>
      </div>
      <div>
        <h2 class="footer-heading">מידע ועזרה</h2>
        <ul class="footer-links">{legal_links}</ul>
      </div>
    </div>
    {render_affiliate_note(site, variant="footer")}
    <div class="footer-bottom">
      <span>&copy; {year} {esc(site['siteName'])}. כל הזכויות שמורות.</span>
      <div class="footer-social">{social_html}</div>
    </div>
  </div>
</footer>
"""


def render_affiliate_note(site, variant="inline"):
    """A plain-language affiliate disclosure, at normal reading size, shown where
    visitors meet product links (home, category and product pages) and in the footer."""
    extra = site.get("affiliateStatement", "").strip()
    extra_html = f" {esc(extra)}" if extra else ""
    text = (
        "הרבה מהקישורים באתר, כולל הכפתורים שמובילים לאמזון, הם קישורי שותפים. "
        "כשותפי אמזון, אנחנו מרוויחים עמלה מרכישות מזכות, בלי עלות נוספת עבורכם. האתר אינו קשור לאמזון ואינו מטעמה."
        f"{extra_html}"
    )
    link = '<a href="/affiliate-disclosure.html">לגילוי הנאות המלא</a>.'
    if variant == "footer":
        return f'<div class="footer-disclosure"><h2 class="footer-heading">גילוי נאות</h2><p>{text} {link}</p></div>'
    return f'<div class="affiliate-note" role="note" aria-label="גילוי נאות"><p>{text} {link}</p></div>'


# --------------------------------------------------------------------------
# Product / category card markup (SSR mirror of the JS components)
# --------------------------------------------------------------------------

def product_index_label(product):
    """A specimen-catalog number derived from the product's own stable id
    (e.g. "prd-0097" -> "No. 097") -- reused data, never invented."""
    num = product["id"].split("-")[-1]
    return f"מס' {num}"


_CARD_SEQ = 0


def render_product_card(product, reveal=True, reveal_delay=0, morph=False, eager=False):
    # Every card gets unique ids so its link can be named by the product title and
    # described by the blurb, price and rating (a product can appear twice on the
    # homepage, so ids are per-render, not per-product). js/components/productCard.js
    # mirrors this with its own "pcj" id space.
    global _CARD_SEQ
    _CARD_SEQ += 1
    cid = f"pc{_CARD_SEQ}"
    reveal_attr = f'data-reveal data-reveal-delay="{reveal_delay}"' if reveal else ""
    # `morph` opts a card into the shared-element image transition (see
    # base.css) -- only safe where a product can appear at most once on the
    # page, since view-transition-name must be unique per document. Skipped
    # on the homepage, where a product can legitimately show up in both the
    # trending rail and the latest grid at once.
    # Only the photo gets a view-transition-name, not the title: the detail
    # page's title already has its own pd-enter entrance animation, and a
    # named element is hidden/restored around the browser's own transition
    # timing -- stacking both would fight rather than compose. The photo
    # morph alone is the dramatic part; the text can just fade with the rest
    # of the root crossfade.
    morph_style = f' style="view-transition-name: product-photo-{product["slug"]}"' if morph else ""
    return f"""
<article class="product-card" {reveal_attr}>
  <a class="product-card-link" href="/product/{product['slug']}/" aria-labelledby="{cid}-name" aria-describedby="{cid}-desc {cid}-meta">
    <div class="product-card__media">
      <img src="{product['image']}" alt="{esc(product['name'])}" loading="{'eager' if eager else 'lazy'}" width="800" height="800"{morph_style}
           onerror="this.onerror=null;this.src='/assets/images/fallback.svg';" />
    </div>
    <div class="product-card__body">
      <span class="product-card__category">{esc(category_label(product['category']))}</span>
      <h3 class="product-card__name" id="{cid}-name">{esc(product['name'])}</h3>
      <p class="product-card__desc visually-line-clamp-2" id="{cid}-desc">{esc(product['shortDescription'])}</p>
      <div class="product-card__meta" id="{cid}-meta">
        <span class="product-card__price">{format_price(product['price'], product['currency'])}</span>
        {render_stars(product['rating'], product['reviewCount'])}
      </div>
    </div>
  </a>
  <div class="product-card__cta">
    <a class="btn--ghost btn--icon-trail" data-affiliate-link data-product-slug="{product['slug']}" aria-label="לצפייה באמזון: {esc(product['name'])} (נפתח בלשונית חדשה)">לצפייה באמזון {CHEVRON_ICON}</a>
  </div>
</article>
"""


def inline_category_svg(slug):
    """Read the category's generated art and embed it directly rather than
    via <img src>, so its .category-tile__icon-path can be reached by CSS
    for the hover stroke-draw -- an externally-referenced image is opaque
    to CSS/JS, an inlined one isn't. Falls back to an <img> reference if the
    file is ever missing so a category tile never renders broken."""
    svg_path = os.path.join(PUBLIC_DIR, "assets", "images", "categories", f"{slug}.svg")
    try:
        with open(svg_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return f'<img src="/assets/images/categories/{slug}.svg" alt="" loading="lazy" width="1200" height="900" />'


def render_category_tile(category, count):
    return f"""
<a class="category-tile" href="/category/{category['slug']}/" data-reveal>
  <div class="category-tile__media">{inline_category_svg(category['slug'])}</div>
  <div class="category-tile__body">
    <h3 class="category-tile__name" style="view-transition-name: category-name-{category['slug']}">{esc(category['name'])}</h3>
    <span class="category-tile__count">{count} מוצרים</span>
  </div>
</a>
"""


def render_collection_tile(collection):
    thumbs = "".join(
        f'<span class="collection-tile__thumb"><img src="{p["image"]}" alt="" loading="lazy" width="200" height="200" /></span>'
        for p in collection["items"][:3]
    )
    n = len(collection["items"])
    return f"""
<a class="collection-tile" href="/collection/{collection['slug']}/" data-reveal>
  <span class="collection-tile__thumbs" aria-hidden="true">{thumbs}</span>
  <span class="collection-tile__body">
    <span class="collection-tile__count">{n} מוצרים</span>
    <h3 class="collection-tile__name">{esc(collection['name'])}</h3>
    <span class="collection-tile__blurb">{esc(collection['blurb'])}</span>
  </span>
</a>
"""


# --------------------------------------------------------------------------
# Base HTML document
# --------------------------------------------------------------------------

def base_page(site, *, title, description, canonical_path, og_image=None, body_html, active_nav=None, page_scripts=None, extra_head="", show_intro=False, lang=None):
    css_links = "\n  ".join(f'<link rel="stylesheet" href="{href}" />' for href in CSS_FILES)
    canonical_url = site["url"].rstrip("/") + canonical_path
    og_image_url = site["url"].rstrip("/") + (og_image or "/assets/logo/og-image.jpg")
    scripts = "".join(f'<script type="module" src="{s}"></script>' for s in (page_scripts or []))
    intro_html = render_brand_intro() if show_intro else ""
    # Search-console ownership tags, e.g. {"google-site-verification": "...", "msvalidate.01": "..."}
    verification_meta = "".join(
        f'<meta name="{esc(name)}" content="{esc(value)}" />' for name, value in (site.get("verification") or {}).items() if value
    )

    return f"""<!doctype html>
<html lang="{lang or site.get('locale', 'he')}" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="p:domain_verify" content="b39d8ea156a82de56d39bfc2ed4cd607" />
  {verification_meta}
  {render_analytics_head(site)}
  {A11Y_HEAD}
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="icon" href="/assets/logo/favicon.ico" sizes="any" />
  <link rel="icon" href="/assets/logo/favicon-32.png" type="image/png" sizes="32x32" />
  <link rel="icon" href="/assets/logo/favicon-192.png" type="image/png" sizes="192x192" />
  <link rel="apple-touch-icon" href="/assets/logo/apple-touch-icon.png" />
  <link rel="manifest" href="/site.webmanifest" />
  <meta name="theme-color" content="#14213d" />

  <meta property="og:type" content="website" />
  <meta property="og:locale" content="he_IL" />
  <meta property="og:site_name" content="{esc(site['siteName'])}" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{canonical_url}" />
  <meta property="og:image" content="{og_image_url}" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(description)}" />
  <meta name="twitter:image" content="{og_image_url}" />

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700;900&family=Heebo:wght@400;500;600;700&display=swap" />
  {css_links}
  {extra_head}
</head>
<body>
  {intro_html}
  {render_header(site, active_nav)}
  {render_site_index(site, _ALL_CATEGORIES, _ALL_COUNTS)}
  {render_search_overlay()}
  {render_a11y_panel()}
  <main id="main-content" tabindex="-1">
  {body_html}
  </main>
  {render_footer(site)}
  <script type="module" src="/js/main.js"></script>
  {scripts}
</body>
</html>
"""


# --------------------------------------------------------------------------
# Homepage
# --------------------------------------------------------------------------

GIFT_BUDGETS = [("עד 25 דולר", 25), ("עד 50 דולר", 50), ("עד 100 דולר", 100)]
GIFT_INTERESTS = [
    ("לאוהבי בישול", "kitchen"), ("לילדים", "kids"), ("לבעלי חיות", "pets"),
    ("לגיימרים", "gaming"), ("לחובבי טכנולוגיה", "tech"), ("לאוהבי טבע וספורט", "outdoors"),
    ("למטיילים", "travel"), ("לבית", "home"),
]


def render_gift_guide(heading_tag="h2", title="מוצאים מתנה מהר"):
    """Budget + interest shortcuts. Budgets open the Gifts grid pre-filtered by
    max price (category.js reads ?max=); interests open the matching category."""
    budgets = "".join(
        f'<a class="gift-guide__budget" href="/category/gifts/?max={amount}">{esc(label)}</a>'
        for label, amount in GIFT_BUDGETS
    )
    interests = "".join(
        f'<a class="gift-guide__interest" href="/category/{slug}/">'
        f'<span>{esc(label)}</span><span class="gift-guide__arrow" aria-hidden="true">&larr;</span></a>'
        for label, slug in GIFT_INTERESTS
    )
    return f"""
<div class="gift-guide">
  <{heading_tag} class="gift-guide__title">{esc(title)}</{heading_tag}>
  <div class="gift-guide__row">
    <span class="gift-guide__label">לפי תקציב</span>
    <div class="gift-guide__budgets">{budgets}</div>
  </div>
  <div class="gift-guide__row">
    <span class="gift-guide__label">לפי תחום עניין</span>
    <div class="gift-guide__interests">{interests}</div>
  </div>
</div>
"""


def render_video_strip(videos):
    """Homepage strip for the newest video: its products in video order, numbered."""
    if not videos:
        return ""
    v = videos[0]
    items = "".join(
        f'<div class="rail__item"><div class="video-item" id="h{i["n"]}">'
        f'<div class="video-item__label"><span class="video-item__num">#{i["n"]}</span> {esc(i["label"])}</div>'
        f'{render_product_card(i["product"], reveal=False, eager=True)}</div></div>'
        for i in v["items"]
    )
    return f"""
<section class="section" id="from-the-videos">
  <div class="container section-head--split" data-reveal="fade">
    <div>
      <span class="eyebrow">מהסרטונים</span>
      <h2 class="section-title">{esc(v['title'])}</h2>
      <p class="section-desc">ראיתם משהו בסרטון האחרון? כל מוצר מחכה כאן תחת אותו מספר. <a href="/v/">לכל הסרטונים</a></p>
    </div>
    <div class="rail-controls">
      <button class="icon-btn" type="button" data-rail-prev="video-rail" aria-label="גלילה אחורה">{CHEVRON_LEFT_ICON}</button>
      <button class="icon-btn" type="button" data-rail-next="video-rail" aria-label="גלילה קדימה">{CHEVRON_ICON}</button>
    </div>
  </div>
  <div class="container">
    <div class="rail" id="video-rail" data-rail role="region" aria-label="מוצרים מהסרטון האחרון">{items}</div>
  </div>
</section>
"""


def render_guides_strip(guides):
    """Homepage section for the gift guides: the season's main way into the catalog."""
    if not guides:
        return ""
    tiles = "".join(render_guide_tile(g) for g in guides[:9])
    return f"""
<section class="section container" id="gift-guides">
  <div class="section-head section-head--split" data-reveal="fade">
    <div>
      <span class="eyebrow">רעיונות למתנה</span>
      <h2 class="section-title">מדריכי מתנות לכל אחד</h2>
      <p class="section-desc">רשימות קצרות ונבחרות לפי אדם ותקציב. כדאי להתחיל כאן אם קונים למישהו אחר.</p>
    </div>
    <a class="btn btn--secondary" href="/guides/">כל {len(guides)} המדריכים {CHEVRON_ICON}</a>
  </div>
  <div class="collection-grid">{tiles}</div>
</section>
"""


def render_homepage(site, categories, products, counts, collections=(), videos=(), guides=()):
    trending = [p for p in products if p.get("trending")][:10]
    latest = sorted(products, key=lambda p: p["createdAt"], reverse=True)[:8]
    collage_source = trending if len(trending) >= 3 else products
    collage = collage_source[:3]

    collage_html = "".join(
        f'<div class="hero-collage__item hero-collage__item--{i+1}"><img src="{p["image"]}" alt="{esc(p["name"])}" loading="eager" /></div>'
        for i, p in enumerate(collage)
    )
    hero = f"""
<section class="hero">
  <div class="container hero__grid">
    <div class="hero__intro">
      <h1 class="hero__title hero-enter hero-enter--1"><span class="accent">שודדים</span> רק את<br/>מה ששווה לקנות.</h1>
      <p class="hero__sub hero-enter hero-enter--2">בלי לגלול שעות בתוצאות חיפוש. אנחנו בוחרים ידנית את הגאדג׳טים, המתנות והרעיונות הקטנים והטובים מאמזון שבאמת שווים את הכסף, עם דירוגים אמיתיים ומחירים שנבדקו.</p>
      <div class="hero__ctas hero-enter hero-enter--3">
        <a class="btn btn--primary" href="{'/guides/' if guides else '#categories'}">{'למדריכי המתנות' if guides else 'לקטלוג'} {CHEVRON_ICON}</a>
        <a class="btn btn--secondary" href="#categories">לכל הקטלוג</a>
        <span class="hero__ctas-note">{len(products):,} מוצרים נבחרים</span>
      </div>
    </div>
    <div class="hero__collage">{collage_html}</div>
  </div>
</section>
<div class="container">{render_affiliate_note(site)}</div>
"""

    trending_cards = "".join(render_product_card(p, reveal_delay=min(i, 3) * 70) for i, p in enumerate(trending))
    trending_section = f"""
<section class="section" id="trending">
  <div class="container section-head--split" data-reveal="fade">
    <div>
      <span class="eyebrow">חם עכשיו</span>
      <h2 class="section-title">הכי פופולריים כרגע</h2>
    </div>
    <div class="rail-controls">
      <button class="icon-btn" type="button" data-rail-prev="trending-rail" aria-label="גלילה אחורה">{CHEVRON_LEFT_ICON}</button>
      <button class="icon-btn" type="button" data-rail-next="trending-rail" aria-label="גלילה קדימה">{CHEVRON_ICON}</button>
    </div>
  </div>
  <div class="container">
    <div class="rail" id="trending-rail" data-rail role="region" aria-label="מוצרים חמים">
      {"".join(f'<div class="rail__item">{card}</div>' for card in [render_product_card(p, reveal=False) for p in trending])}
    </div>
  </div>
</section>
"""

    category_tiles = "".join(render_category_tile(c, counts.get(c["slug"], 0)) for c in categories)
    category_section = f"""
<section class="section container" id="categories">
  <div class="section-head" data-reveal="fade">
    <div>
      <span class="eyebrow">עיון</span>
      <h2 class="section-title">קונים לפי קטגוריה</h2>
      <p class="section-desc">{len(categories)} דרכים להיכנס לקטלוג.</p>
    </div>
  </div>
  <div class="category-bento">{category_tiles}</div>
</section>
"""
    collections_section = ""
    if collections:
        tiles = "".join(render_collection_tile(c) for c in collections)
        collections_section = f"""
<section class="section container" id="collections">
  <div class="section-head" data-reveal="fade">
    <div>
      <span class="eyebrow">אוספים</span>
      <h2 class="section-title">נבחרים לפי נושא</h2>
      <p class="section-desc">לא בטוחים מאיפה להתחיל? בחרו נושא.</p>
    </div>
  </div>
  <div class="collection-grid">{tiles}</div>
</section>
"""

    latest_cards = "".join(render_product_card(p, reveal_delay=min(i, 3) * 70) for i, p in enumerate(latest))
    latest_section = f"""
<section class="section container" id="latest">
  <div class="section-head" data-reveal="fade">
    <div>
      <span class="eyebrow">חדש באתר</span>
      <h2 class="section-title">הצטרפו עכשיו לקטלוג</h2>
    </div>
  </div>
  <div class="grid-products grid-products--feature">{latest_cards}</div>
</section>
"""

    # Fewer, calmer sections: the products are the focus, not the page chrome.
    body = (hero + render_guides_strip(guides) + render_video_strip(videos) + category_section + trending_section
            + collections_section + latest_section)

    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site["siteName"],
        "url": site["url"],
        "logo": site["url"].rstrip("/") + "/assets/logo/favicon-512.png",
        "description": site["description"],
    })
    extra_head = f'<script type="application/ld+json">{ld_json}</script>'

    return base_page(
        site,
        title=f"{site['siteName']} | מוצרים שווים מאמזון ורעיונות למתנה",
        description=f"{len(products):,} מוצרים נבחרים מאמזון עם דירוגים אמיתיים ומחירים שנבדקו, ומדריכי מתנות לכל אחד ולכל תקציב.",
        canonical_path="/",
        body_html=body,
        active_nav="home",
        page_scripts=["/js/pages/home.js"],
        extra_head=extra_head,
        show_intro=False,
    )


# --------------------------------------------------------------------------
# Category pages
# --------------------------------------------------------------------------

PAGE_SIZE = 24

# <title> per category: the phrase people actually search, not just the label.
CATEGORY_TITLES = {
    "tech": "גאדג׳טים וטכנולוגיה מאמזון",
    "home": "מוצרים לבית מאמזון",
    "kitchen": "גאדג׳טים למטבח מאמזון",
    "gaming": "ציוד גיימינג ומשחקי קופסה מאמזון",
    "kids": "צעצועים ומתנות לילדים מאמזון",
    "outdoors": "ציוד לטיולים ולספורט מאמזון",
    "pets": "מוצרים לכלבים וחתולים מאמזון",
    "travel": "ציוד לנסיעות ולרכב מאמזון",
    "desk-setup": "אביזרים לשולחן העבודה מאמזון",
    "gifts": "רעיונות למתנה מאמזון",
    "under-25": "מוצרים מאמזון עד 25 דולר",
}


def popularity(p):
    """Mirror of sortProducts('popular') in js/core/store.js: rating weighted by
    how many reviews back it up, so a 4.8 with 50k reviews outranks a 5.0 with 12."""
    return (p.get("rating") or 0) * math.log10((p.get("reviewCount") or 0) + 10)


def render_category_page(site, category, all_categories, category_products):
    initial_sorted = sorted(category_products, key=popularity, reverse=True)
    # Only the first page is server-rendered (keeps the HTML small on phones);
    # js/pages/category.js renders the rest behind a "Show more" button.
    cards = "".join(render_product_card(p, reveal=False, morph=True) for p in initial_sorted[:PAGE_SIZE]) if initial_sorted else ""
    gift_block = render_gift_guide() if category["slug"] == "gifts" else ""

    empty_state = """
<div class="state-panel">
  <svg class="state-panel__icon" viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><path d="M4 7l1-3h14l1 3M4 7h16M4 7l1 13h14l1-13"/></svg>
  <p class="state-panel__title">עדיין אין כאן מוצרים</p>
  <p>מוצרים חדשים בדרך, כדאי לחזור בקרוב.</p>
</div>
"""

    sub_counts = {}
    for p in category_products:
        if p.get("subcategory"):
            sub_counts[p["subcategory"]] = sub_counts.get(p["subcategory"], 0) + 1
    top_subs = sorted(((k, v) for k, v in sub_counts.items() if v >= 2), key=lambda kv: (-kv[1], kv[0]))[:8]
    subcategory_group = ""
    if len(top_subs) >= 2:
        chips = "".join(
            f'<button type="button" class="chip" data-filter-sub="{esc(name)}" aria-pressed="false">{esc(name)}'
            f'<span class="chip__count" aria-hidden="true">{n}</span><span class="sr-only"> ({n})</span></button>'
            for name, n in top_subs
        )
        subcategory_group = (
            '<div class="filter-group" role="group" aria-labelledby="filter-type-title">'
            '<h2 class="filter-group__title" id="filter-type-title">סוג</h2>'
            f'<div class="filter-chips">{chips}</div></div>'
        )

    body = f"""
<section class="page-hero category-hero">
  <div class="category-hero__watermark"><img src="/assets/images/categories/{category['slug']}.svg" alt="" /></div>
  <div class="container category-hero__content">
    {render_breadcrumbs([("דף הבית", "/"), ("קטגוריות", "/#categories"), (category['name'], None)])}
    <span class="eyebrow">קטגוריה</span>
    <h1 class="section-title" style="font-size: var(--fs-display-xl); view-transition-name: category-name-{category['slug']};">{esc(category['name'])}</h1>
    <p class="category-hero__desc">{esc(category['description'])}</p>
  </div>
</section>
{f'<section class="container">{gift_block}</section>' if gift_block else ''}
<section class="section container">
  <div class="category-layout" data-category-app data-category-slug="{category['slug']}">
    <div class="category-filters" role="group" aria-label="סינון מוצרים">
      <div class="input-field" style="margin-bottom: var(--space-lg);">
        {SEARCH_ICON}
        <input type="search" placeholder="חיפוש ב{esc(category['name'])}…" data-category-search aria-label="חיפוש ב{esc(category['name'])}" autocomplete="off" enterkeyhint="search" spellcheck="false" />
      </div>
      <details class="filters-more" open data-filters-more>
      <summary class="filters-more__toggle">סינון</summary>
      {subcategory_group}
      <div class="filter-group" role="group" aria-labelledby="filter-rating-title">
        <h2 class="filter-group__title" id="filter-rating-title">דירוג</h2>
        <div class="filter-chips">
          <button type="button" class="chip" data-filter-rating="4.5" aria-pressed="false">4.5+<span class="sr-only"> כוכבים ומעלה</span></button>
          <button type="button" class="chip" data-filter-rating="4" aria-pressed="false">4.0+<span class="sr-only"> כוכבים ומעלה</span></button>
          <button type="button" class="chip" data-filter-rating="3.5" aria-pressed="false">3.5+<span class="sr-only"> כוכבים ומעלה</span></button>
        </div>
      </div>
      <div class="filter-group" role="group" aria-labelledby="filter-price-title">
        <h2 class="filter-group__title" id="filter-price-title">מחיר (דולר)</h2>
        <div class="filter-price">
          <div class="input-field"><input type="number" min="0" step="any" inputmode="decimal" autocomplete="off" placeholder="מ-" data-filter-min-price aria-label="מחיר מינימלי בדולרים" /></div>
          <div class="input-field"><input type="number" min="0" step="any" inputmode="decimal" autocomplete="off" placeholder="עד" data-filter-max-price aria-label="מחיר מקסימלי בדולרים" /></div>
        </div>
      </div>
      <div class="filter-group" role="group" aria-labelledby="filter-show-title">
        <h2 class="filter-group__title" id="filter-show-title">הצגה בלבד</h2>
        <label class="filter-checkbox"><input type="checkbox" data-filter-featured /> מומלצים</label>
        <label class="filter-checkbox"><input type="checkbox" data-filter-trending /> חמים</label>
      </div>
      <button type="button" class="btn btn--secondary btn--sm btn--full" data-filters-clear>ניקוי הסינון</button>
      </details>
      <script>(function(){{var d=document.querySelector('[data-filters-more]');if(d&&matchMedia('(max-width: 900px)').matches)d.removeAttribute('open');}})();</script>
    </div>
    <div>
      <div class="toolbar">
        <span class="toolbar__count" data-result-count role="status" aria-live="polite">{len(initial_sorted)} מוצרים</span>
        <div class="toolbar__controls">
          <div class="input-field select-field">
            <select data-sort-select aria-label="מיון מוצרים">
              <option value="popular">הכי פופולריים</option>
              <option value="featured">מומלצים</option>
              <option value="trending">חמים</option>
              <option value="newest">החדשים ביותר</option>
              <option value="price-asc">מחיר: מהנמוך לגבוה</option>
              <option value="price-desc">מחיר: מהגבוה לנמוך</option>
              <option value="rating">דירוג</option>
            </select>
          </div>
        </div>
      </div>
      {render_affiliate_note(site)}
      <div class="grid-products grid-products--feature" data-category-grid>{cards if cards else ''}</div>
      <div class="load-more" data-load-more-wrap{'' if len(initial_sorted) > PAGE_SIZE else ' hidden'}>
        <p class="load-more__status" data-load-more-status>מוצגים {min(PAGE_SIZE, len(initial_sorted))} מתוך {len(initial_sorted)}</p>
        <button type="button" class="btn btn--secondary" data-load-more>להציג עוד</button>
      </div>
      {'' if cards else empty_state}
    </div>
  </div>
</section>
"""

    return base_page(
        site,
        title=CATEGORY_TITLES.get(category["slug"], f"{category['name']} מאמזון") + f" | {site['siteName']}",
        description=category["description"],
        canonical_path=f"/category/{category['slug']}/",
        # Social cards can't show SVG, so the category's most popular product photo is used.
        og_image=initial_sorted[0]["image"] if initial_sorted else None,
        body_html=body,
        page_scripts=["/js/pages/category.js"],
        active_nav=category["slug"],
    )


def render_collection_page(site, collection):
    cards = "".join(render_product_card(p, reveal=False, morph=True) for p in collection["items"])
    n = len(collection["items"])
    body = f"""
<section class="page-hero container">
  {render_breadcrumbs([("דף הבית", "/"), ("אוספים", "/#collections"), (collection['name'], None)])}
  <span class="eyebrow">אוסף</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">{esc(collection['name'])}</h1>
  <p class="category-hero__desc">{esc(collection['blurb'])}</p>
</section>
<section class="section container">
  <h2 class="sr-only">המוצרים באוסף</h2>
  <div class="toolbar"><span class="toolbar__count" role="status">{n} מוצרים</span></div>
  {render_affiliate_note(site)}
  <div class="grid-products grid-products--feature" data-collection-grid>{cards}</div>
</section>
"""
    return base_page(
        site,
        title=f"{collection['name']} | {site['siteName']}",
        description=collection["blurb"],
        canonical_path=f"/collection/{collection['slug']}/",
        og_image=collection["items"][0]["image"],
        body_html=body,
        page_scripts=["/js/pages/collection.js"],
    )


# --------------------------------------------------------------------------
# Gift guides (/guides/): the search- and Pinterest-facing pages. Each is a numbered
# list of picks with a short editorial intro and FAQ, built from data/guides.json.
# --------------------------------------------------------------------------

def guide_updated(guide):
    """The newest price check among a guide's picks, as 'Month YYYY'."""
    newest = max((p.get("updatedAt") or p.get("createdAt") or "")[:10] for p in guide["items"])
    y, m, _ = newest.split("-")
    return f"{_MONTHS[int(m) - 1]} {y}"


def render_guide_tile(guide):
    thumbs = "".join(
        f'<span class="collection-tile__thumb"><img src="{p["image"]}" alt="" loading="lazy" width="200" height="200" /></span>'
        for p in guide["items"][:3]
    )
    return f"""
<a class="collection-tile guide-tile" href="/guides/{guide['slug']}/">
  <span class="collection-tile__thumbs" aria-hidden="true">{thumbs}</span>
  <span class="collection-tile__body">
    <span class="collection-tile__count">{len(guide['items'])} מוצרים</span>
    <h3 class="collection-tile__name">{esc(guide['title'])}</h3>
    <span class="collection-tile__blurb">{esc(guide['card'])}</span>
  </span>
</a>
"""


def render_guide_item(n, p, site):
    price = format_price(p["price"], p["currency"])
    return f"""
<li class="guide-item" id="pick-{n}">
  <a class="guide-item__media" href="/product/{p['slug']}/" tabindex="-1" aria-hidden="true">
    <img src="{p['image']}" alt="" loading="{'eager' if n <= 2 else 'lazy'}" width="800" height="800" onerror="this.onerror=null;this.src='/assets/images/fallback.svg';" />
  </a>
  <div class="guide-item__body">
    <span class="guide-item__num">{n:02d}</span>
    <span class="product-card__category">{esc(category_label(p['category']))}{' · ' + esc(p['subcategory']) if p.get('subcategory') else ''}</span>
    <h2 class="guide-item__name"><a href="/product/{p['slug']}/">{esc(p['name'])}</a></h2>
    <div class="guide-item__meta"><span class="product-card__price">{price}</span>{render_stars(p['rating'], p['reviewCount'])}</div>
    <p class="guide-item__why"><strong>למה זה כאן:</strong> {esc(p['whyWeLikeIt'])} {esc(p['shortDescription'])}</p>
    <div class="guide-item__cta">
      <a class="btn btn--primary" data-affiliate-link data-product-slug="{p['slug']}" aria-label="בדיקת מחיר באמזון: {esc(p['name'])} (נפתח בלשונית חדשה)">בדיקת מחיר באמזון {CHEVRON_ICON}</a>
      <a class="guide-item__more" href="/product/{p['slug']}/">פרטים</a>
    </div>
  </div>
</li>
"""


def render_guide_page(site, guide, guides):
    items = guide["items"]
    prices = [p["price"] for p in items if p.get("price") is not None]
    intro = "".join(f"<p>{esc(par)}</p>" for par in guide["intro"])
    jump = "".join(f'<a class="video-jump__num" href="#pick-{i}">{i}</a>' for i in range(1, len(items) + 1))
    picks = "".join(render_guide_item(i, p, site) for i, p in enumerate(items, 1))
    faqs = "".join(
        f'<details class="guide-faq__item"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in guide.get("faqs", [])
    )
    by_slug = {g["slug"]: g for g in guides}
    related = [by_slug[s] for s in guide.get("related", []) if s in by_slug]
    related_html = "".join(render_guide_tile(g) for g in related)
    updated = guide_updated(guide)
    price_range = f"${min(prices):,.0f} עד ${max(prices):,.0f}" if prices else ""
    body = f"""
<section class="page-hero container guide-hero">
  {render_breadcrumbs([("דף הבית", "/"), ("מדריכי מתנות", "/guides/"), (guide['title'], None)])}
  <span class="eyebrow">מדריך מתנות · עודכן {esc(updated)}</span>
  <h1 class="section-title guide-hero__title">{esc(guide['title'])}</h1>
  <div class="guide-hero__intro">{intro}</div>
  <p class="guide-hero__facts tag-mono">{len(items)} מוצרים · {esc(price_range)} · המחירים נבדקו באמזון ארה״ב</p>
  <nav class="video-jump" aria-label="מעבר למוצר">{jump}</nav>
</section>
<section class="section container">
  {render_affiliate_note(site)}
  <ol class="guide-list">{picks}</ol>
</section>
<section class="section container guide-faq">
  <h2 class="section-title">שאלות נפוצות</h2>
  {faqs}
</section>
<section class="section container">
  <span class="eyebrow">עוד רעיונות</span>
  <h2 class="section-title">עוד מדריכי מתנות</h2>
  <div class="collection-grid">{related_html}</div>
  <p class="guide-all"><a class="btn btn--secondary" href="/guides/">כל מדריכי המתנות {CHEVRON_ICON}</a></p>
</section>
"""
    base = site["url"].rstrip("/")
    ld = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": guide["title"],
         "itemListElement": [{"@type": "ListItem", "position": i, "url": f"{base}/product/{p['slug']}/", "name": p["name"]}
                             for i, p in enumerate(items, 1)]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "דף הבית", "item": base + "/"},
            {"@type": "ListItem", "position": 2, "name": "מדריכי מתנות", "item": base + "/guides/"},
            {"@type": "ListItem", "position": 3, "name": guide["title"], "item": f"{base}/guides/{guide['slug']}/"}]},
    ]
    if guide.get("faqs"):
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in guide["faqs"]]})
    extra_head = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    return base_page(
        site,
        title=guide["metaTitle"],
        description=guide["metaDescription"],
        canonical_path=f"/guides/{guide['slug']}/",
        og_image=items[0]["image"],
        body_html=body,
        active_nav="guides",
        page_scripts=["/js/pages/collection.js"],
        extra_head=extra_head,
    )


def render_guides_index(site, guides):
    tiles = "".join(render_guide_tile(g) for g in guides)
    body = f"""
<section class="page-hero container">
  {render_breadcrumbs([("דף הבית", "/"), ("מדריכי מתנות", None)])}
  <span class="eyebrow">רעיונות למתנה</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">מדריכי מתנות</h1>
  <p class="category-hero__desc">רשימות קצרות ונבחרות לכל אדם ולכל תקציב. כל מוצר הוא מוצר אמיתי מאמזון עם דירוג גבוה, והמחירים נבדקים באמזון ארה״ב.</p>
  {render_gift_guide(heading_tag="h2", title="קונים לפי תקציב או תחום עניין")}
</section>
<section class="section container">
  <h2 class="sr-only">כל מדריכי המתנות</h2>
  <div class="collection-grid">{tiles}</div>
</section>
"""
    return base_page(
        site,
        title=f"מדריכי מתנות: רעיונות למתנה לכל אחד | {site['siteName']}",
        description="מדריכי מתנות מאמזון: מתנות לו, לה, לילדים, לנוער, לגיימרים, לאוהבי קפה ולמטיילים, בכל תקציב.",
        canonical_path="/guides/",
        og_image=guides[0]["items"][0]["image"],
        body_html=body,
        active_nav="guides",
    )


def render_hebrew_page(site, guides):
    """/he/: how buying from Amazon to Israel works."""
    links = "".join(
        f'<a class="he-guide" href="/guides/{g["slug"]}/"><span>{esc(g["title"])}</span>'
        f'<span class="he-guide__count">{len(g["items"])} מוצרים</span></a>'
        for g in guides
    )
    body = f"""
<section class="page-hero container he-page">
  <span class="eyebrow">מדריך קצר</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">איך קונים מאמזון לישראל</h1>
  <p class="category-hero__desc">כל מוצר באתר הוא מוצר אמיתי מאמזון ארה״ב עם דירוג גבוה, והמחירים מוצגים בדולרים. כך זה עובד:</p>
</section>
<section class="section container he-page">
  <ol class="he-steps">
    <li>לוחצים על הכפתור <strong>בדיקת מחיר באמזון</strong> ליד המוצר. הקישור פותח את עמוד המוצר באמזון בלשונית חדשה.</li>
    <li>באמזון בודקים את המחיר העדכני, אם המוצר נשלח לישראל ומה עלות המשלוח. לא כל מוצר נשלח לישראל. אמזון מציעה משלוח חינם לישראל על מוצרים מסוימים בהזמנה מעל $49, וזה מופיע בעמוד המוצר כשהם זכאים.</li>
    <li>מוצרים חשמליים מארה״ב מיועדים בדרך כלל למתח של 120 וולט, ובישראל המתח הוא 230 וולט. כדאי לבדוק זאת לפני שקונים.</li>
    <li>משלמים ישירות באמזון. אנחנו לא מוכרים כלום בעצמנו ולא רואים את פרטי ההזמנה. ייתכנו מע״מ ומכס לפי הכללים בישראל.</li>
  </ol>
  <p class="he-note">הקישורים באתר הם קישורי שותפים: אם קונים דרכם, ייתכן שנקבל עמלה מאמזון, בלי עלות נוספת עבורכם. <a href="/affiliate-disclosure.html">לגילוי הנאות</a>.</p>
</section>
<section class="section container he-page">
  <h2 class="section-title">מדריכי מתנות</h2>
  <div class="he-guides">{links}</div>
</section>
"""
    return base_page(
        site,
        title=f"איך קונים מאמזון לישראל | {site['siteName']}",
        description="מדריך קצר: איך קונים מאמזון לישראל, מה לבדוק לפני ההזמנה ומה עם משלוח, מתח חשמל ומיסים.",
        canonical_path="/he/",
        og_image=guides[0]["items"][0]["image"] if guides else None,
        body_html=body,
    )


# --------------------------------------------------------------------------
# Video landing pages (/v/): the link-in-bio destination. Each page lists the
# products of one video under the numbers the video shows, so a viewer who
# wants "#3" taps 3 and lands on it.
# --------------------------------------------------------------------------

def render_video_list(videos, current_slug=None):
    rows = "".join(
        f'<li><a class="video-list__link{" is-current" if v["slug"] == current_slug else ""}" href="/v/{v["slug"]}/">'
        f'<span class="video-list__title">{esc(v["title"])}</span>'
        f'<span class="video-list__count tag-mono">{len(v["items"])} מוצרים</span></a></li>'
        for v in videos
    )
    return f'<ul class="video-list">{rows}</ul>'


def render_video_body(site, video, videos, eyebrow):
    jump = "".join(f'<a class="video-jump__num" href="#n{i["n"]}">{i["n"]}</a>' for i in video["items"])
    cards = "".join(
        f"""
<div class="video-item" id="n{i['n']}">
  <div class="video-item__label"><span class="video-item__num">#{i['n']}</span> {esc(i['label'])}</div>
  {render_product_card(i['product'], reveal=False)}
</div>"""
        for i in video["items"]
    )
    return f"""
<section class="page-hero container video-hero">
  <span class="eyebrow">{esc(eyebrow)}</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">{esc(video['title'])}</h1>
  <p class="category-hero__desc">{esc(video['blurb'])}</p>
  <nav class="video-jump" aria-label="מעבר למספר">{jump}</nav>
  <p class="video-links"><a href="/guides/">מדריכי מתנות</a> · <a href="/he/">איך קונים מאמזון לישראל</a></p>
</section>
<section class="section container">
  <h2 class="sr-only">המוצרים בסרטון</h2>
  {render_affiliate_note(site)}
  <div class="video-grid">{cards}</div>
</section>
<section class="section container">
  <h2 class="section-title">כל הסרטונים</h2>
  {render_video_list(videos, video['slug'])}
</section>
"""


def render_video_page(site, video, videos):
    return base_page(
        site,
        title=f"{video['title']} | {site['siteName']}",
        description=f"המוצרים מהסרטון “{video['title']}”, לפי המספר.",
        canonical_path=f"/v/{video['slug']}/",
        og_image=video["items"][0]["product"]["image"],
        body_html=render_video_body(site, video, videos, "מהסרטון"),
        page_scripts=["/js/pages/video.js"],
    )


def render_videos_index(site, videos):
    latest = videos[0]
    return base_page(
        site,
        title=f"מהסרטונים | {site['siteName']}",
        description="כל המוצרים מהסרטונים שלנו, לפי המספר. הסרטון החדש ראשון.",
        canonical_path="/v/",
        og_image=latest["items"][0]["product"]["image"],
        body_html=render_video_body(site, latest, videos, "הסרטון החדש"),
        page_scripts=["/js/pages/video.js"],
    )


# --------------------------------------------------------------------------
# Product detail pages
# --------------------------------------------------------------------------

def render_product_page(site, product, category, related_products, featured_in=()):
    images = [product["image"]] + product.get("additionalImages", [])
    featured_html = ""
    if featured_in:
        links = "".join(f'<li><a href="/guides/{g["slug"]}/">{esc(g["title"])}</a></li>' for g in featured_in)
        featured_html = f'<div class="featured-in"><h2 class="featured-in__title">מופיע במדריכים</h2><ul>{links}</ul></div>'
    thumbs_html = ""
    if len(images) > 1:
        thumbs = "".join(
            f'<button type="button" class="product-detail__thumb{" is-active" if i == 0 else ""}" '
            f'data-gallery-thumb data-full-src="{img}" aria-pressed="{"true" if i == 0 else "false"}" '
            f'aria-label="תמונה {i+1} מתוך {len(images)}"><img src="{img}" alt="" loading="lazy" width="72" height="72" /></button>'
            for i, img in enumerate(images)
        )
        thumbs_html = f'<div class="product-detail__thumbs">{thumbs}</div>'

    highlights = "".join(
        f'<li><svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 10l4 4 8-9"/></svg><span>{esc(h)}</span></li>'
        for h in product.get("highlights", [])
    )

    related_section = ""
    if related_products:
        related_items = "".join(
            f'<div class="rail__item">{render_product_card(p, reveal=False, morph=True)}</div>' for p in related_products
        )
        related_section = f"""
<section class="section">
  <div class="container section-head--split" data-reveal="fade">
    <div><span class="eyebrow">אולי יעניין אתכם</span><h2 class="section-title">עוד בסגנון</h2></div>
    <div class="rail-controls">
      <button class="icon-btn" type="button" data-rail-prev="related-rail" aria-label="גלילה אחורה">{CHEVRON_LEFT_ICON}</button>
      <button class="icon-btn" type="button" data-rail-next="related-rail" aria-label="גלילה קדימה">{CHEVRON_ICON}</button>
    </div>
  </div>
  <div class="container">
    <div class="rail" id="related-rail" data-rail>{related_items}</div>
  </div>
</section>
"""

    # Our own YouTube explainer for this product (data/products.json "youtube": {id, title, uploadDate, duration}),
    # embedded and marked up as a VideoObject so the page can show as a video result.
    yt = product.get("youtube")
    video_html = ""
    if yt:
        video_html = (
            f'<div class="product-video" style="margin-top:1.5rem"><h2 class="featured-in__title">צפו: מה כדאי לדעת לפני שקונים</h2>'
            f'<div style="position:relative;padding-top:56.25%;border-radius:14px;overflow:hidden;background:#000">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{yt["id"]}" title="{esc(yt["title"])}" loading="lazy" '
            f'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen '
            f'style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe></div></div>'
        )

    body = f"""
<section class="section container" data-product-app data-product-slug="{product['slug']}">
  {render_breadcrumbs([("דף הבית", "/"), (category['name'], f"/category/{category['slug']}/"), (product['name'], None)])}
  <div class="product-detail">
    <div class="product-detail__gallery pd-gallery-enter">
      <div class="product-detail__gallery-main"><img src="{product['image']}" alt="{esc(product['name'])}" data-gallery-main loading="eager" style="view-transition-name: product-photo-{product['slug']}" /></div>
      {thumbs_html}
    </div>
    <div>
      <div class="pd-enter pd-enter--1">
        <span class="product-detail__category">{esc(category_label(product['category']))}{' · ' + esc(product['subcategory']) if product.get('subcategory') else ''}</span>
      </div>
      <h1 class="product-detail__title pd-enter pd-enter--2">{esc(product['name'])}</h1>
      <div class="product-detail__meta-row pd-enter pd-enter--3">
        <span class="product-detail__price">{format_price(product['price'], product['currency'])}</span>
        {render_stars(product['rating'], product['reviewCount'])}
      </div>
      {f'<p class="product-detail__price-note pd-enter pd-enter--3">המחיר נבדק ב-{esc(format_date_long(product["updatedAt"][:10]))} באמזון ארה״ב, לפני משלוח ומיסים לישראל. המחירים משתנים, אז כדאי לבדוק את המחיר העדכני באמזון.</p>' if product.get('price') is not None and product.get('updatedAt') else ''}
      {'<p class="product-detail__stock-note pd-enter pd-enter--3">כרגע קשה למצוא אותו חדש באמזון. מוצרים דומים למטה.</p>' if product.get('availability') == 'unavailable' else ''}
      <div class="cta-panel pd-enter pd-enter--3">
        <a class="btn btn--primary btn--full" data-affiliate-link data-product-slug="{product['slug']}" aria-label="בדיקת מחיר באמזון: {esc(product['name'])} (נפתח בלשונית חדשה)">בדיקת מחיר באמזון {CHEVRON_ICON}</a>
        <p class="cta-panel__disclaimer"><strong>לפני ההזמנה, בדקו באמזון שהמוצר נשלח לישראל ומה עלות המשלוח.</strong> נפתח בלשונית חדשה. קישור שותפים: ייתכן שנקבל עמלה, בלי עלות נוספת עבורכם. <a href="/affiliate-disclosure.html">גילוי נאות</a>.</p>
      </div>
      <div class="pd-enter pd-enter--4">
        <h2 class="sr-only">על המוצר</h2>
        <p class="product-detail__desc">{esc(product['description'])}</p>
        <div class="why-we-like-it">
          <div class="why-we-like-it__label">למה אהבנו</div>
          <p>{esc(product['whyWeLikeIt'])}</p>
        </div>
        <h2 class="sr-only">עיקרי המוצר</h2>
        <ul class="highlights-list">{highlights}</ul>
        {video_html}
        {featured_html}
      </div>
    </div>
  </div>
  <div class="mobile-cta" data-mobile-cta aria-hidden="true">
    <span class="mobile-cta__price">{format_price(product['price'], product['currency'])}</span>
    <a class="btn btn--primary" data-affiliate-link data-product-slug="{product['slug']}" tabindex="-1">בדיקת מחיר {CHEVRON_ICON}</a>
  </div>
</section>
{related_section}
"""

    ld_json = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product["name"],
        "description": product["shortDescription"],
        "image": site["url"].rstrip("/") + product["image"],
    }
    # The maker's brand, as Amazon lists it (data/products.json "brand"); omitted when unknown
    # rather than guessed. Star ratings are Amazon's, not reviews collected here, so they are
    # shown on the page but not marked up as this site's aggregateRating.
    if product.get("brand"):
        ld_json["brand"] = {"@type": "Brand", "name": product["brand"]}
    if product.get("price") is not None:
        ld_json["offers"] = {
            "@type": "Offer",
            "price": product["price"],
            "priceCurrency": product["currency"],
            "availability": "https://schema.org/OutOfStock" if product.get("availability") == "unavailable" else "https://schema.org/InStock",
            "url": site["url"].rstrip("/") + f"/product/{product['slug']}/",
        }
    extra_head = f'<script type="application/ld+json">{json.dumps(ld_json, ensure_ascii=False)}</script>'
    if yt:
        video_ld = {
            "@context": "https://schema.org", "@type": "VideoObject", "name": yt["title"],
            "description": f"מה כתוב באמזון על {product['name']}, הדירוג והמחיר.",
            "thumbnailUrl": f"https://i.ytimg.com/vi/{yt['id']}/hqdefault.jpg", "uploadDate": yt["uploadDate"],
            "duration": yt["duration"], "embedUrl": f"https://www.youtube.com/embed/{yt['id']}",
            "contentUrl": f"https://www.youtube.com/watch?v={yt['id']}",
        }
        extra_head += f'<script type="application/ld+json">{json.dumps(video_ld)}</script>'

    # The snippet Google shows: what it is, then the checked price and Amazon rating.
    meta_bits = [product["shortDescription"].rstrip(".") + "."]
    if product.get("price") is not None:
        meta_bits.append(f"{format_price(product['price'], product['currency'])} באמזון")
    if product.get("rating") and product.get("reviewCount"):
        meta_bits.append(f"דירוג {product['rating']:.1f}/5 מתוך {product['reviewCount']:,} ביקורות")
    meta_desc = meta_bits[0] + (" " + ", ".join(meta_bits[1:]) + "." if len(meta_bits) > 1 else "")

    return base_page(
        site,
        title=f"{product['name']} | {site['siteName']}",
        description=meta_desc,
        canonical_path=f"/product/{product['slug']}/",
        og_image=product["image"],
        body_html=body,
        page_scripts=["/js/pages/product.js"],
        extra_head=extra_head,
    )


# --------------------------------------------------------------------------
# Static content pages
# --------------------------------------------------------------------------

def render_about_page(site):
    n = esc(site["siteName"])
    body = f"""
<section class="page-hero container">
  {render_breadcrumbs([("דף הבית", "/"), ("אודות", None)])}
  <span class="eyebrow">אודות</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">אנחנו מוצאים את הדברים המעניינים קודם.</h1>
  <p class="about-hero__lede">{n} מאתר מוצרים מעניינים, גאדג׳טים שימושיים ודברים ששווה להכיר, וחוסך לכם את השעות שהיה לוקח למצוא אותם לבד.</p>
</section>
<section class="section container narrow">
  <div class="prose">
    <p>אנחנו עוברים על הזרם האינסופי של מוצרים חדשים כדי שאתם לא תצטרכו, ומסננים את הרעש ואת מה שנראה טוב רק בתמונה.</p>
    <p>אנחנו לא חנות ולא מייצרים כלום. כשמוצר מרוויח מקום אצלנו, אנחנו מפנים אתכם למקום שבו אפשר לקנות אותו. זה כל המודל: גילוי, הצגה ישרה, בלי לחץ לקנות.</p>
  </div>
  <hr class="hr" />
  <div class="value-grid">
    <div data-reveal>
      <div class="value-item__num">01</div>
      <div class="value-item__title">נבחר ידנית</div>
      <div class="value-item__desc">כל מוצר כאן נבחר בכוונה, ולא יובא אוטומטית מרשימה.</div>
    </div>
    <div data-reveal>
      <div class="value-item__num">02</div>
      <div class="value-item__title">בנוי למבט מהיר</div>
      <div class="value-item__desc">הגעתם מסרטון, ראיתם משהו טוב, המשכתם הלאה. בלי הרשמה ובלי חיכוך.</div>
    </div>
    <div data-reveal>
      <div class="value-item__num">03</div>
      <div class="value-item__title">שקופים לגבי המודל</div>
      <div class="value-item__desc">ייתכן שנקבל עמלה על חלק מהקישורים. זה לא קובע מה מופיע כאן. <a href="/affiliate-disclosure.html">לגילוי הנאות</a>.</div>
    </div>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"אודות | {site['siteName']}",
        description=f"{site['siteName']} בוחר מוצרים מעניינים ושימושיים מאמזון, כדי שלא תצטרכו לחפש אותם שעות.",
        canonical_path="/about.html",
        body_html=body,
        active_nav="about",
    )


def render_legal_page(site, *, eyebrow, title, slug, description, lead_html, sections_html):
    """Shared shell for the legal / accessibility pages: breadcrumb, h1, a clearly
    dated 'last updated' line, then plain prose. One place, so all of them stay
    consistent with each other and with the rest of the site."""
    updated = site["legalUpdated"]
    body = f"""
<section class="page-hero container">
  {render_breadcrumbs([("דף הבית", "/"), (title, None)])}
  <span class="eyebrow">{esc(eyebrow)}</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">{esc(title)}</h1>
  <p class="legal-updated">עודכן לאחרונה: <time datetime="{updated}">{format_date_long(updated)}</time></p>
</section>
<section class="section container narrow">
  <div class="prose">
    {lead_html}
    {sections_html}
  </div>
</section>
"""
    return base_page(
        site,
        title=f"{title} | {site['siteName']}",
        description=description,
        canonical_path=f"/{slug}",
        body_html=body,
    )


def render_accessibility_page(site):
    n = esc(site["siteName"])
    d = format_date_long(site["legalUpdated"])
    lead = f"<p>{n} רוצה שכל אחד יוכל לגלוש בקטלוג, גם בעזרת מקלדת, קורא מסך, הגדלה, שליטה קולית או מסך מגע. אנחנו רואים בנגישות עבודה מתמשכת.</p>"
    sections = f"""
    <h2>התקן שאליו אנחנו שואפים</h2>
    <p>אנחנו פועלים להתאמה להנחיות הנגישות לתכני אינטרנט (WCAG) 2.2 ברמה AA ולתקן הישראלי ת״י 5568.</p>

    <h2>מצב נוכחי</h2>
    <p>האתר לא עבר ביקורת או הסמכה חיצונית, ואיננו טוענים להתאמה מלאה. האתר עבר לאחרונה לעברית ולכיוון כתיבה מימין לשמאל, ובדיקות הנגישות שנעשו לפני המעבר טרם חזרו על עצמן במלואן על הגרסה הזו. לא בדקנו עדיין עם קוראי מסך ייעודיים או עם משתמשים עם מוגבלות, ולכן ייתכן שנותרו בעיות.</p>

    <h2>מה עשינו</h2>
    <ul>
      <li>קישור ״דילוג לתוכן הראשי״ בתחילת כל עמוד.</li>
      <li>כל האפשרויות זמינות במקלדת עם מסגרת מיקוד גלויה. התפריט, החיפוש ואפשרויות הנגישות נסגרים במקש Escape ומחזירים את המיקוד לכפתור שפתח אותם.</li>
      <li>כותרות, רשימות, כפתורים וקישורים בקוד HTML תקני. תמונות מוצרים כוללות טקסט חלופי, ואיורים דקורטיביים מוסתרים מקוראי מסך.</li>
      <li>צבעי הטקסט נבחרו בהתאם לדרישות הניגודיות של WCAG.</li>
      <li>העמודים מתאימים את עצמם למסכים צרים ולטקסט מוגדל, והגדלת הדפדפן לעולם לא חסומה.</li>
      <li>האנימציות מכבדות את הגדרת הפחתת התנועה במכשיר, והתוכן לא תלוי בהן.</li>
    </ul>

    <h2>אפשרויות הנגישות באתר</h2>
    <p>הכפתור <strong>אפשרויות נגישות</strong> בראש העמוד פותח חלונית עם:</p>
    <ul>
      <li><strong>גודל טקסט:</strong> חמש דרגות, עד 175%.</li>
      <li><strong>ניגודיות גבוהה:</strong> טקסט שחור על לבן עם גבולות חזקים יותר.</li>
      <li><strong>הפחתת תנועה:</strong> מכבה מעברים ואפקטים.</li>
      <li><strong>איפוס הכול:</strong> חזרה לברירת המחדל.</li>
    </ul>
    <p>הבחירות נשמרות רק בדפדפן שלכם (ראו <a href="/cookie-notice.html">מדיניות עוגיות</a>) ולא נשלחות אלינו.</p>

    <h2>מגבלות ידועות</h2>
    <ul>
      <li>חלק מתמונות המוצרים מגיעות מאמזון וכוללות טקסט באנגלית בתוך התמונה. שמות המותגים והדגמים מופיעים באנגלית.</li>
      <li>הכפתורים לאמזון מקבלים את היעד שלהם באמצעות סקריפט. אם סקריפטים חסומים, הכפתורים לא יעבדו.</li>
      <li>כשעוברים לאמזון יוצאים מהאתר, ונגישות האתר שם אינה בשליטתנו. עמודי המוצר באמזון אינם בעברית.</li>
      <li>הגופנים נטענים מ-Google Fonts. אם הם חסומים, יוצג גופן חלופי.</li>
    </ul>

    <h2 id="report">דיווח על בעיית נגישות</h2>
    <p>אם משהו באתר קשה או בלתי אפשרי לשימוש, או שאתם צריכים מידע בפורמט אחר, ספרו לנו. כדאי לציין את כתובת העמוד, מה ניסיתם לעשות, מה השתבש, ובאיזה דפדפן וטכנולוגיה מסייעת השתמשתם.</p>
    {render_contact_paragraph(site)}

    <h2>תאריך עדכון</h2>
    <p>ההצהרה עודכנה לאחרונה ב-<time datetime="{site['legalUpdated']}">{d}</time>.</p>
"""
    return render_legal_page(
        site, eyebrow="נגישות", title="הצהרת נגישות", slug="accessibility.html",
        description="איך אנחנו מטפלים בנגישות, מה נבדק, מגבלות ידועות ואיך מדווחים על בעיה.",
        lead_html=lead, sections_html=sections,
    )


def render_cookie_page(site):
    n = esc(site["siteName"])
    lead = f"<p>העמוד הזה מסביר מה {n} שומר במכשיר שלכם ואילו צדדים שלישיים מעורבים כשאתם משתמשים באתר.</p>"
    sections = f"""
    <h2>בקצרה</h2>
    <p>האתר לא מגדיר עוגיות משלו ולא משתמש בעוגיות פרסום או במעקב פרסומי. ספירת הביקורים והקליקים נעשית ב-Umami, שירות אנליטיקה שלא משתמש בעוגיות ולא מזהה אתכם. בדפדפן נשמרת העדפה קטנה בלבד, ולכן אין באנר הסכמה לעוגיות.</p>

    <h2>מה נשמר בדפדפן</h2>
    <dl class="legal-list">
      <dt><code>pf-a11y</code> &middot; local storage</dt>
      <dd>זוכר את בחירות הנגישות שלכם. נוצר רק אם שיניתם אחת מהן, ונמחק באיפוס או בניקוי נתוני הדפדפן. המידע לא נשלח אלינו או לצד שלישי.</dd>
    </dl>

    <h2>צדדים שלישיים</h2>
    <ul>
      <li><strong>Google Fonts.</strong> הגופנים נטענים משרתי Google, שמקבלים את כתובת ה-IP ופרטי הדפדפן שלכם.</li>
      <li><strong>Umami.</strong> סקריפט מ-cloud.umami.is סופר צפיות בעמודים וקליקים על הכפתורים לאמזון. הוא לא שומר עוגיות ולא בונה עליכם פרופיל.</li>
      <li><strong>GitHub Pages.</strong> האתר מתארח שם, ו-GitHub מקבלת מידע בקשה רגיל כמו כתובת IP.</li>
      <li><strong>אמזון.</strong> כשעוברים לאמזון יוצאים מהאתר. אמזון ותוכנית השותפים עשויות להשתמש בעוגיות, כולל כדי לתעד שרכישה הגיעה דרכנו, לפי המדיניות שלהן.</li>
    </ul>

    <h2>ניהול הנתונים</h2>
    <p>אפשר למחוק את המידע בהגדרות הדפדפן, או להשתמש ב<strong>איפוס הכול</strong> באפשרויות הנגישות.</p>
    {render_contact_paragraph(site, "שאלות על העמוד הזה? ")}
"""
    return render_legal_page(
        site, eyebrow="מידע משפטי", title="מדיניות עוגיות", slug="cookie-notice.html",
        description="מה נשמר בדפדפן שלכם ואילו צדדים שלישיים מעורבים בשימוש באתר.",
        lead_html=lead, sections_html=sections,
    )


def render_affiliate_disclosure_page(site):
    n = esc(site["siteName"])
    extra = site.get("affiliateStatement", "").strip()
    extra_html = f"<p>{esc(extra)}</p>" if extra else ""
    lead = (
        '<div class="callout"><p><strong>בקצרה:</strong> הרבה מהקישורים באתר, כולל הכפתורים שמובילים לאמזון, הם קישורי שותפים. '
        "כשותפי אמזון, אנחנו מרוויחים עמלה מרכישות מזכות, בלי עלות נוספת עבורכם.</p></div>"
    )
    sections = f"""
    {extra_html}
    <h2>מה זה האתר</h2>
    <p>{n} הוא אתר עצמאי לגילוי מוצרים. אנחנו בוחרים מוצרים שנראים לנו מעניינים או שימושיים, מתארים אותם ומקשרים לחנות שבה אפשר לקנות אותם, בעיקר אמזון.</p>

    <h2>איך הקישורים עובדים</h2>
    <p>כשלוחצים על כפתור לאמזון יוצאים מהאתר ומגיעים לאמזון, לפעמים דרך קישור מקוצר כמו <code>link.amazon</code>. אמזון עשויה להשתמש בעוגיות כדי לתעד שהגעתם דרכנו. אם תקנו, ייתכן שנקבל עמלה לפי תנאי התוכנית. המחיר שלכם זהה בכל מקרה.</p>

    <h2>מה קורה באתר של אמזון</h2>
    <p>אנחנו לא מוכרים כלום ולא מעבדים רכישות. תשלום, משלוח, החזרות, אחריות ושירות לקוחות מטופלים על ידי אמזון או המוכר, לפי התנאים שלהם. אנחנו לא רואים את פרטי התשלום או ההזמנה.</p>

    <h2>מה זה לא משנה</h2>
    <p>{n} הוא אתר עצמאי, <strong>אינו קשור לאמזון, אינו מטעמה ואינו ממומן על ידה</strong> או על ידי מותג אחר שמוזכר באתר, אלא אם נכתב אחרת במפורש. עמלה לא משנה את המחיר שאתם משלמים.</p>

    <h2>מחירים, דירוגים ומשלוח לישראל</h2>
    <p>המחירים מוצגים בדולרים לפי אמזון ארה״ב ואינם כוללים משלוח, מע״מ או מכס. מחירים, זמינות, משלוחים וביקורות משתנים. לא כל מוצר נשלח לישראל, ומוצרים חשמליים עשויים להתאים למתח 120 וולט בלבד. הדירוגים נלקחו מאמזון כשהמוצר נוסף לאתר וייתכן שהשתנו. יש לבדוק את הפרטים העדכניים באמזון לפני קנייה.</p>
    {render_contact_paragraph(site, "שאלות על קישור או על הגילוי הזה? ")}
"""
    return render_legal_page(
        site, eyebrow="מידע משפטי", title="גילוי נאות", slug="affiliate-disclosure.html",
        description="איך האתר משתמש בקישורי שותפים, מה קורה כשלוחצים עליהם ומה זה לא משנה.",
        lead_html=lead, sections_html=sections,
    )


def render_privacy_page(site):
    n = esc(site["siteName"])
    lead = f"<p>{n} בנוי כך שייאסף עליכם כמה שפחות מידע. העמוד הזה מסביר בשפה פשוטה מה זה אומר בפועל.</p>"
    sections = f"""
    <h2>מי אחראי</h2>
    <p>{n} הוא אתר עצמאי. לשאלות על המדיניות אפשר להשתמש בפרטי הקשר בסוף העמוד.</p>

    <h2>מה נאסף</h2>
    <ul>
      <li><strong>כלום דרך האתר עצמו.</strong> אין חשבונות, הרשמה, טפסים או תשלומים, ולכן איננו מבקשים שם, מייל או פרטי תשלום.</li>
      <li><strong>אם תכתבו לנו במייל</strong> נקבל את הכתובת שלכם ואת תוכן ההודעה, ונשתמש בהם רק כדי להשיב.</li>
      <li><strong>חיפושים וסינון נשארים בדפדפן.</strong> מה שאתם מקלידים לא נשלח אלינו.</li>
      <li><strong>ספירת ביקורים וקליקים אנונימית</strong> באמצעות Umami, כולל פרטים כלליים כמו עמוד, אתר מפנה, מדינה וסוג מכשיר. אין זיהוי של מבקרים, עוגיות או מעקב פרסומי.</li>
      <li><strong>העדפות קטנות במכשיר.</strong> בחירות נגישות נשמרות בדפדפן. ראו <a href="/cookie-notice.html">מדיניות עוגיות</a>.</li>
    </ul>

    <h2>צדדים שלישיים</h2>
    <ul>
      <li><strong>GitHub Pages</strong> מארח את האתר ומקבל מידע בקשה רגיל כמו כתובת IP.</li>
      <li><strong>Umami</strong> (cloud.umami.is) מספק את הספירה האנונימית.</li>
      <li><strong>Google Fonts</strong> מספק את הגופנים ומקבל את כתובת ה-IP ופרטי הדפדפן.</li>
      <li><strong>אמזון.</strong> כשעוברים לאמזון, אמזון ותוכנית השותפים מטפלות במידע לפי המדיניות שלהן. איננו מקבלים פרטי חשבון, הזמנה או תשלום.</li>
    </ul>

    <h2>ילדים</h2>
    <p>האתר אינו מיועד לילדים ואינו אוסף ביודעין מידע אישי מאף אחד.</p>

    <h2>הזכויות שלכם</h2>
    <p>לפי חוק הגנת הפרטיות, התשמ״א-1981, ניתן לפנות אלינו בכל בקשה בנוגע למידע שאולי מוחזק אצלנו, כמו התכתבות במייל. אפשר גם למחוק את מה שנשמר בדפדפן ולחסום בקשות לצדדים שלישיים.</p>

    <h2>שינויים במדיניות</h2>
    <p>אם נתחיל לאסוף משהו חדש, העמוד יעודכן לפני כן והתאריך למעלה ישתנה.</p>

    <h2>יצירת קשר</h2>
    {render_contact_paragraph(site)}
"""
    return render_legal_page(
        site, eyebrow="מידע משפטי", title="מדיניות פרטיות", slug="privacy-policy.html",
        description="מה נאסף (מעט מאוד), אילו צדדים שלישיים מעורבים ומה האפשרויות שלכם.",
        lead_html=lead, sections_html=sections,
    )


def render_terms_page(site):
    n = esc(site["siteName"])
    lead = f"<p>התנאים האלה מתארים איך אפשר להשתמש ב{n} ועל מה האתר אחראי. אם אינכם מסכימים להם, נא לא להשתמש באתר.</p>"
    sections = f"""
    <h2>מה זה האתר</h2>
    <p>{n} הוא אתר עצמאי לגילוי מוצרים. הוא לא חנות ולא מוכר. הוא לא מוכר מוצרים, לא גובה תשלום, לא שולח סחורה ולא מטפל בהחזרות, אחריות או שירות לקוחות. כל רכישה נעשית באתר של המוכר, בדרך כלל אמזון, והיא עניין בינכם לבינו. האתר אינו קשור לאמזון ואינו מטעמה.</p>

    <h2>מידע על מוצרים</h2>
    <p>שמות, תיאורים, דירוגים, תמונות וקישורים מוצגים לצורך מידע, והתיאורים תורגמו ונכתבו על בסיס הדף באמזון. מחירים, זמינות, מפרטים, משלוחים ותאימות, כולל משלוח לישראל והתאמה למתח החשמל בישראל, נקבעים על ידי המוכרים ועשויים להשתנות. יש לוודא את הפרטים באתר המוכר לפני קנייה.</p>

    <h2>קישורי שותפים</h2>
    <p>הרבה מהקישורים הם קישורי שותפים, וייתכן שנקבל עמלה אם תקנו דרכם, בלי עלות נוספת עבורכם. ראו <a href="/affiliate-disclosure.html">גילוי נאות</a>.</p>

    <h2>אתרים של צד שלישי</h2>
    <p>הקישורים מובילים לאתרים שאינם בבעלותנו, ואיננו אחראים לתוכן, למדיניות או לנגישות שלהם.</p>

    <h2>לא ייעוץ מקצועי</h2>
    <p>התוכן באתר הוא מידע כללי. הוא אינו ייעוץ מקצועי, בטיחותי, רפואי, פיננסי או משפטי. יש לפעול לפי הוראות היצרן.</p>

    <h2>תוכן ובעלות</h2>
    <p>הכתיבה, הבחירה והעיצוב שייכים ל{n}. שמות מוצרים, מותגים, סימני מסחר ותמונות מוצרים שייכים לבעליהם ומוצגים כדי לזהות את המוצרים. אם אתם בעלי זכויות במשהו באתר וחושבים שנעשה בו שימוש שגוי, פנו אלינו.</p>

    <h2>זמינות ואחריות</h2>
    <p>האתר מסופק כפי שהוא, בלי התחייבות לזמינות או לדיוק. במידה שהחוק מתיר, איננו אחראים לנזקים שנובעים מהחלטות על מוצרים או מוכרים. אין בתנאים אלה כדי לגרוע מזכויות שלא ניתן להתנות עליהן לפי הדין בישראל.</p>

    <h2>שינויים בתנאים</h2>
    <p>התנאים עשויים להתעדכן. התאריך למעלה מציין מתי עודכנו לאחרונה.</p>

    <h2>יצירת קשר</h2>
    {render_contact_paragraph(site)}
"""
    return render_legal_page(
        site, eyebrow="מידע משפטי", title="תנאי שימוש", slug="terms.html",
        description="תנאי השימוש באתר: מה האתר, איך עובדים מידע על מוצרים וקישורי שותפים, ומה הגבולות.",
        lead_html=lead, sections_html=sections,
    )


def render_404_page(site):
    body = """
<section class="container error-page">
  <div>
    <div class="error-page__code">404</div>
    <h1 class="section-title" style="margin-top: var(--space-sm);">הדף הזה נשדד.</h1>
    <p class="section-desc" style="margin: var(--space-sm) auto var(--space-lg);">הדף שחיפשתם לא קיים או שעבר למקום אחר.</p>
    <a class="btn btn--primary" href="/">חזרה לדף הבית</a>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"הדף לא נמצא | {site['siteName']}",
        description="הדף לא קיים או שעבר למקום אחר.",
        canonical_path="/404.html",
        body_html=body,
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

_ALL_CATEGORIES = []
_ALL_COUNTS = {}


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    global _ALL_CATEGORIES, _ALL_COUNTS
    site, categories, products = load_data()
    _ALL_CATEGORIES = categories

    published = [p for p in products if p.get("published")]
    counts = {}
    for p in published:
        for slug in [p["category"], *p.get("secondaryCategories", [])]:
            counts[slug] = counts.get(slug, 0) + 1
    _ALL_COUNTS = counts

    # ---- Client-side data snapshot (mirrors a future public API response) ----
    # Only the fields the browser uses (cards, search, filters, sorting), minified:
    # the full records are ~4x larger and every page loads this file.
    client_fields = ("id", "name", "slug", "category", "subcategory", "secondaryCategories", "shortDescription",
                     "tags", "image", "price", "currency", "rating", "reviewCount", "affiliateUrl",
                     "featured", "trending", "published", "createdAt")
    snapshot = [{k: p[k] for k in client_fields if k in p} for p in published]
    write_file(os.path.join(PUBLIC_DIR, "data", "products.json"), json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
    write_file(os.path.join(PUBLIC_DIR, "data", "categories.json"), json.dumps(categories, indent=2, ensure_ascii=False))

    # ---- Homepage ----
    collections = []
    videos = load_videos(published)
    guides = load_guides(published)
    write_file(os.path.join(PUBLIC_DIR, "index.html"), render_homepage(site, categories, published, counts, collections, videos, guides))

    # ---- Gift guides ----
    if guides:
        write_file(os.path.join(PUBLIC_DIR, "guides", "index.html"), render_guides_index(site, guides))
        for guide in guides:
            write_file(os.path.join(PUBLIC_DIR, "guides", guide["slug"], "index.html"), render_guide_page(site, guide, guides))
        write_file(os.path.join(PUBLIC_DIR, "he", "index.html"), render_hebrew_page(site, guides))
    guides_by_product = {}
    for guide in guides:
        for p in guide["items"]:
            guides_by_product.setdefault(p["slug"], []).append(guide)

    # ---- Collection pages ----
    for collection in collections:
        write_file(
            os.path.join(PUBLIC_DIR, "collection", collection["slug"], "index.html"),
            render_collection_page(site, collection),
        )

    # ---- Video landing pages ----
    if videos:
        write_file(os.path.join(PUBLIC_DIR, "v", "index.html"), render_videos_index(site, videos))
        for video in videos:
            write_file(
                os.path.join(PUBLIC_DIR, "v", video["slug"], "index.html"),
                render_video_page(site, video, videos),
            )

    # ---- Category pages ----
    for category in categories:
        cat_products = [p for p in published if product_in_category(p, category["slug"])]
        write_file(
            os.path.join(PUBLIC_DIR, "category", category["slug"], "index.html"),
            render_category_page(site, category, categories, cat_products),
        )

    # ---- Product pages ----
    categories_by_slug = {c["slug"]: c for c in categories}
    for product in published:
        category = categories_by_slug[product["category"]]
        related = related_products(product, published)
        write_file(
            os.path.join(PUBLIC_DIR, "product", product["slug"], "index.html"),
            render_product_page(site, product, category, related, guides_by_product.get(product["slug"], [])[:3]),
        )

    # ---- Static pages ----
    write_file(os.path.join(PUBLIC_DIR, "about.html"), render_about_page(site))
    write_file(os.path.join(PUBLIC_DIR, "affiliate-disclosure.html"), render_affiliate_disclosure_page(site))
    write_file(os.path.join(PUBLIC_DIR, "privacy-policy.html"), render_privacy_page(site))
    write_file(os.path.join(PUBLIC_DIR, "terms.html"), render_terms_page(site))
    write_file(os.path.join(PUBLIC_DIR, "accessibility.html"), render_accessibility_page(site))
    write_file(os.path.join(PUBLIC_DIR, "cookie-notice.html"), render_cookie_page(site))
    write_file(os.path.join(PUBLIC_DIR, "404.html"), render_404_page(site))

    # ---- robots.txt / sitemap.xml / manifest ----
    base_url = site["url"].rstrip("/")
    urls = ["/", "/about.html", "/affiliate-disclosure.html", "/privacy-policy.html", "/terms.html",
            "/accessibility.html", "/cookie-notice.html"]
    if guides:
        urls += ["/guides/"] + [f"/guides/{g['slug']}/" for g in guides] + ["/he/"]
    urls += [f"/category/{c['slug']}/" for c in categories]
    urls += [f"/collection/{c['slug']}/" for c in collections]
    if videos:
        urls += ["/v/"] + [f"/v/{v['slug']}/" for v in videos]
    urls += [f"/product/{p['slug']}/" for p in published]
    # lastmod from the data itself (newest price check), so it only moves when content does.
    newest = max((p.get("updatedAt") or p.get("createdAt") or "")[:10] for p in published)
    product_dates = {f"/product/{p['slug']}/": (p.get("updatedAt") or p.get("createdAt") or newest)[:10] for p in published}
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{base_url}{u}</loc><lastmod>{product_dates.get(u, newest)}</lastmod></url>\n" for u in urls)
    sitemap += "</urlset>\n"
    write_file(os.path.join(PUBLIC_DIR, "sitemap.xml"), sitemap)
    # Split sitemaps + an index under fresh names (GSC kept "couldn't fetch" on the first sitemap.xml of this
    # new property). sitemap-pages: guides, videos, categories; sitemap-products: the catalog.
    def _urlset(us):
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{base_url}{u}</loc><lastmod>{product_dates.get(u, newest)}</lastmod></url>\n" for u in us)
                + "</urlset>\n")
    write_file(os.path.join(PUBLIC_DIR, "sitemap-pages.xml"), _urlset([u for u in urls if not u.startswith("/product/")]))
    write_file(os.path.join(PUBLIC_DIR, "sitemap-products.xml"), _urlset([u for u in urls if u.startswith("/product/")]))
    write_file(os.path.join(PUBLIC_DIR, "sitemap_index.xml"),
               '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "".join(f"  <sitemap><loc>{base_url}/{n}</loc><lastmod>{newest}</lastmod></sitemap>\n"
                         for n in ("sitemap-pages.xml", "sitemap-products.xml"))
               + "</sitemapindex>\n")
    # IndexNow (Bing, Yandex, Seznam, Naver): the key file proves we own the host when
    # scripts/indexnow.py submits changed URLs.
    if site.get("indexNowKey"):
        write_file(os.path.join(PUBLIC_DIR, f"{site['indexNowKey']}.txt"), site["indexNowKey"])

    write_file(os.path.join(PUBLIC_DIR, "robots.txt"), f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\nSitemap: {base_url}/sitemap_index.xml\n")

    manifest = {
        "name": site["siteName"],
        "short_name": site["siteName"],
        "description": site["description"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#14213d",
        "theme_color": "#14213d",
        "icons": [
            {"src": "/assets/logo/favicon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/logo/favicon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/assets/logo/maskable-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    write_file(os.path.join(PUBLIC_DIR, "site.webmanifest"), json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"Built {len(urls)} pages ({len(published)} products across {len(categories)} categories, "
          f"{len(products) - len(published)} unpublished/hidden).")


if __name__ == "__main__":
    main()
