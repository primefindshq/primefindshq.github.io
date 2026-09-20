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

def load_data():
    with open(os.path.join(DATA_DIR, "site-config.json"), encoding="utf-8") as f:
        site = json.load(f)
    with open(os.path.join(DATA_DIR, "categories.json"), encoding="utf-8") as f:
        categories = json.load(f)
    with open(os.path.join(DATA_DIR, "products.json"), encoding="utf-8") as f:
        products = json.load(f)
    return site, categories, products


# --------------------------------------------------------------------------
# Small formatting helpers (mirrors of js/core/utils.js, server-side)
# --------------------------------------------------------------------------

def esc(value):
    return html.escape(str(value), quote=True)


def format_price(price, currency="USD"):
    if price is None:
        return "Check price"
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
        label = f"{rating:.1f} out of 5" + (f" ({review_count:,} reviews)" if review_count else "")
        extra = f'<span>{rating:.1f}</span>'
        if review_count:
            extra += f'<span class="text-faint">({review_count:,})</span>'
    else:
        label = "Not yet rated"
        extra = '<span class="text-faint">New</span>'
    return f'<span class="rating" role="img" aria-label="{esc(label)}"><span class="stars">{stars}</span>{extra}</span>'


def category_label(slug):
    return slug.replace("-", " ")


_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def format_date_long(iso):
    """'2026-09-20' -> '20 September 2026' (unambiguous for an international audience)."""
    y, m, d = (int(part) for part in iso.split("-"))
    return f"{d} {_MONTHS[m - 1]} {y}"


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
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>'


def render_contact_paragraph(site, lead=""):
    """The one place that decides how a visitor can reach PRIME.FINDS. Only channels
    that actually exist are offered: an email address if one has been configured in
    data/site-config.json, and the public issue tracker of the site's repository."""
    contact = site.get("contact", {})
    email = contact.get("email", "").strip()
    issues = contact.get("issuesUrl", "").strip()
    bits = []
    if email:
        bits.append(f'by email at <a href="mailto:{esc(email)}">{esc(email)}</a>')
    if issues:
        bits.append(
            f'through the site\'s <a href="{esc(issues)}" target="_blank" rel="noopener">public issue tracker on GitHub</a> '
            f'(a free GitHub account is needed, and what you post there is public, so please do not include personal details)'
        )
    if not bits:
        return ""
    joined = " or ".join(bits)
    note = "" if email else " PRIME.FINDS does not currently publish an email address or phone number; this page will be updated if that changes."
    return f"<p>{lead}You can reach PRIME.FINDS {joined}.{note}</p>"


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
CHEVRON_ICON = '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 5l6 5-6 5"/></svg>'
CHEVRON_LEFT_ICON = '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M13 5l-6 5 6 5"/></svg>'
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


def render_header(site, active=None):
    return f"""
<a class="skip-link" href="#main-content">Skip to main content</a>
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])} home">
      <img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1075" height="580" />
    </a>
    <div class="header-actions">
      <button class="icon-btn" type="button" data-search-open aria-haspopup="dialog" aria-label="Search products">{SEARCH_ICON}</button>
      <button class="icon-btn" type="button" data-a11y-toggle aria-haspopup="dialog" aria-expanded="false" aria-controls="a11y-panel" aria-label="Accessibility options">{A11Y_ICON}</button>
      <button class="index-trigger" type="button" data-index-toggle aria-expanded="false" aria-haspopup="dialog" aria-controls="site-index" aria-label="Site index">
        <span class="index-trigger__glyph" aria-hidden="true"><span></span><span></span></span>
        <span class="index-trigger__label">Index</span>
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
<div class="site-index" id="site-index" data-index-panel role="dialog" aria-modal="true" aria-label="Site index">
  <div class="site-index__top">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])} home"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1075" height="580" /></a>
    <button class="icon-btn" type="button" data-index-close aria-label="Close site index">{CLOSE_ICON}</button>
  </div>
  <div class="site-index__body">
    <nav aria-label="Pages"><ul class="site-index__nav-list">{nav_links}</ul></nav>
    <nav aria-label="Categories">
      <span class="eyebrow site-index__cats-label">The Catalog</span>
      <div class="site-index__cats">{cat_items}</div>
    </nav>
  </div>
  <div class="site-index__footer">
    <p>{esc(site['tagline'])}</p>
    <nav aria-label="Legal and accessibility"><ul class="site-index__legal">{legal_items}</ul></nav>
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
<div class="brand-intro" data-brand-intro role="group" aria-label="PRIME.FINDS introduction">
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
    <button type="button" class="brand-intro__skip" data-intro-skip>Skip intro</button>
    <a class="brand-intro__link" href="/accessibility.html">Accessibility</a>
  </div>
</div>
"""


def render_search_overlay():
    return f"""
<div class="search-overlay" data-search-overlay role="dialog" aria-modal="true" aria-labelledby="search-overlay-title">
  <div class="search-overlay__panel">
    <h2 class="sr-only" id="search-overlay-title">Search products</h2>
    <div class="search-overlay__input-row">
      {SEARCH_ICON}
      <input class="search-overlay__input" type="search" placeholder="Search products, categories, tags…" data-search-input aria-label="Search products" autocomplete="off" enterkeyhint="search" spellcheck="false" />
      <button class="icon-btn" type="button" data-search-close aria-label="Close search">{CLOSE_ICON}</button>
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
    <h2 class="a11y-panel__title" id="a11y-panel-title">Accessibility options</h2>
    <button class="icon-btn" type="button" data-a11y-close aria-label="Close accessibility options">{CLOSE_ICON}</button>
  </div>
  <div class="a11y-panel__body">
    <div class="a11y-row" role="group" aria-labelledby="a11y-text-label">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-text-label">Text size</span>
        <span class="a11y-row__hint">Currently <span data-a11y-text-value>100%</span></span>
      </div>
      <div class="a11y-stepper">
        <button type="button" class="a11y-btn" data-a11y-text-down>Smaller text</button>
        <button type="button" class="a11y-btn" data-a11y-text-up>Larger text</button>
      </div>
    </div>
    <div class="a11y-row">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-contrast-label">High contrast</span>
        <span class="a11y-row__hint">Stronger text, borders and focus outlines.</span>
      </div>
      <button type="button" class="a11y-switch" role="switch" aria-checked="false" aria-labelledby="a11y-contrast-label" data-a11y-contrast><span class="a11y-switch__knob" aria-hidden="true"></span></button>
    </div>
    <div class="a11y-row">
      <div class="a11y-row__text">
        <span class="a11y-row__label" id="a11y-motion-label">Reduce motion</span>
        <span class="a11y-row__hint" data-a11y-motion-hint>Calmer transitions and a simplified intro.</span>
      </div>
      <button type="button" class="a11y-switch" role="switch" aria-checked="false" aria-labelledby="a11y-motion-label" data-a11y-motion><span class="a11y-switch__knob" aria-hidden="true"></span></button>
    </div>
  </div>
  <div class="a11y-panel__foot">
    <button type="button" class="btn btn--secondary btn--sm" data-a11y-reset>Reset all</button>
    <a class="a11y-panel__link" href="/accessibility.html">Accessibility statement</a>
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
        f'<a href="{esc(instagram)}" target="_blank" rel="noopener" aria-label="PRIME.FINDS on Instagram (opens in a new tab)">{INSTAGRAM_ICON}</a>'
        if instagram
        else f'<span aria-hidden="true">{INSTAGRAM_ICON}</span>'
    )
    year = "2026"
    return f"""
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand-logo" href="/"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])} home" width="1075" height="580" /></a>
        <p class="footer-brand__tagline">{esc(site['tagline'])}</p>
      </div>
      <div>
        <h2 class="footer-heading">Explore</h2>
        <ul class="footer-links">{nav_links}</ul>
      </div>
      <div>
        <h2 class="footer-heading">Categories</h2>
        <ul class="footer-links">{categories_links}</ul>
      </div>
      <div>
        <h2 class="footer-heading">Legal &amp; help</h2>
        <ul class="footer-links">{legal_links}</ul>
      </div>
    </div>
    {render_affiliate_note(site, variant="footer")}
    <div class="footer-bottom">
      <span>&copy; {year} {esc(site['siteName'])}. All rights reserved.</span>
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
        "Many links on PRIME.FINDS, including the &ldquo;View at Amazon&rdquo; buttons, are affiliate links. "
        "If you buy through them, PRIME.FINDS may earn a commission from qualifying purchases, at no extra cost to you."
        f"{extra_html}"
    )
    link = '<a href="/affiliate-disclosure.html">Read the full affiliate disclosure</a>.'
    if variant == "footer":
        return f'<div class="footer-disclosure"><h2 class="footer-heading">Affiliate disclosure</h2><p>{text} {link}</p></div>'
    return f'<div class="affiliate-note" role="note" aria-label="Affiliate disclosure"><p>{text} {link}</p></div>'


# --------------------------------------------------------------------------
# Product / category card markup (SSR mirror of the JS components)
# --------------------------------------------------------------------------

def product_index_label(product):
    """A specimen-catalog number derived from the product's own stable id
    (e.g. "prd-0097" -> "No. 097") -- reused data, never invented."""
    num = product["id"].split("-")[-1]
    return f"No. {num}"


_CARD_SEQ = 0


def render_product_card(product, reveal=True, reveal_delay=0, morph=False):
    # Every card gets unique ids so its link can be named by the product title and
    # described by the blurb, price and rating (a product can appear twice on the
    # homepage, so ids are per-render, not per-product). js/components/productCard.js
    # mirrors this with its own "pcj" id space.
    global _CARD_SEQ
    _CARD_SEQ += 1
    cid = f"pc{_CARD_SEQ}"
    badges = ""
    if product.get("trending"):
        badges += '<span class="badge badge--gold">Trending</span>'
    if product.get("featured"):
        badges += '<span class="badge badge--outline-gold">Featured</span>'
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
      <span class="product-card__index tag-mono" aria-hidden="true">{product_index_label(product)}</span>
      <div class="product-card__badges">{badges}</div>
      <img src="{product['image']}" alt="{esc(product['name'])}" loading="lazy" width="800" height="800"{morph_style}
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
    <a class="btn--ghost btn--icon-trail" data-affiliate-link data-product-slug="{product['slug']}" aria-label="View at Amazon: {esc(product['name'])} (opens in a new tab)">View at Amazon {CHEVRON_ICON}</a>
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
    <span class="category-tile__count">{count:02d} {'find' if count == 1 else 'finds'}</span>
  </div>
</a>
"""


# --------------------------------------------------------------------------
# Base HTML document
# --------------------------------------------------------------------------

def base_page(site, *, title, description, canonical_path, og_image=None, body_html, active_nav=None, page_scripts=None, extra_head="", show_intro=False):
    css_links = "\n  ".join(f'<link rel="stylesheet" href="{href}" />' for href in CSS_FILES)
    canonical_url = site["url"].rstrip("/") + canonical_path
    og_image_url = site["url"].rstrip("/") + (og_image or "/assets/logo/og-image.jpg")
    scripts = "".join(f'<script type="module" src="{s}"></script>' for s in (page_scripts or []))
    intro_html = render_brand_intro() if show_intro else ""

    return f"""<!doctype html>
<html lang="{site.get('locale', 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  {A11Y_HEAD}
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="icon" href="/assets/logo/favicon.ico" sizes="any" />
  <link rel="icon" href="/assets/logo/favicon-32.png" type="image/png" sizes="32x32" />
  <link rel="icon" href="/assets/logo/favicon-192.png" type="image/png" sizes="192x192" />
  <link rel="apple-touch-icon" href="/assets/logo/apple-touch-icon.png" />
  <link rel="manifest" href="/site.webmanifest" />
  <meta name="theme-color" content="#060607" />

  <meta property="og:type" content="website" />
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
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,500&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" />
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

def render_homepage(site, categories, products, counts):
    trending = [p for p in products if p.get("trending")][:10]
    latest = sorted(products, key=lambda p: p["createdAt"], reverse=True)[:8]
    featured = next((p for p in products if p.get("featured")), products[0] if products else None)
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
      <h1 class="hero__title hero-enter hero-enter--1">DISCOVER WHAT'S<br/><span class="accent">worth</span> buying.</h1>
      <p class="hero__sub hero-enter hero-enter--2">No endless scrolling through search results. PRIME.FINDS curates the gadgets, gear and small good ideas actually worth your money.</p>
      <div class="hero__ctas hero-enter hero-enter--3">
        <a class="btn btn--primary" href="#trending">Enter the Catalog {CHEVRON_ICON}</a>
        <span class="hero__ctas-note">{len(products):02d} finds, curated</span>
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
      <span class="eyebrow">Trending Now</span>
      <h2 class="section-title">What everyone's clicking on</h2>
    </div>
    <div class="rail-controls">
      <button class="icon-btn" type="button" data-rail-prev="trending-rail" aria-label="Scroll trending back">{CHEVRON_LEFT_ICON}</button>
      <button class="icon-btn" type="button" data-rail-next="trending-rail" aria-label="Scroll trending forward">{CHEVRON_ICON}</button>
    </div>
  </div>
  <div class="container">
    <div class="rail" id="trending-rail" data-rail role="region" aria-label="Trending products">
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
      <span class="eyebrow">Browse</span>
      <h2 class="section-title">Shop by category</h2>
      <p class="section-desc">Seven ways into the catalog, with more added as we curate further.</p>
    </div>
  </div>
  <div class="category-bento">{category_tiles}</div>
</section>
"""

    editorial_section = ""
    if featured:
        editorial_section = f"""
<section class="section container">
  <div class="editorial" data-reveal="scale">
    <div class="editorial__media"><img src="{featured['image']}" alt="{esc(featured['name'])}" loading="lazy" /></div>
    <div class="editorial__text">
      <span class="editorial__label">Editorial Pick</span>
      <p class="editorial__quote">&ldquo;{esc(featured['whyWeLikeIt'])}&rdquo;</p>
      <span class="editorial__name">{esc(featured['name'])}</span>
      <span class="editorial__price">{format_price(featured['price'], featured['currency'])}</span>
      <div>
        <a class="btn btn--primary" href="/product/{featured['slug']}/">See the Full Story {CHEVRON_ICON}</a>
      </div>
    </div>
  </div>
</section>
"""

    latest_cards = "".join(render_product_card(p, reveal_delay=min(i, 3) * 70) for i, p in enumerate(latest))
    latest_section = f"""
<section class="section container" id="latest">
  <div class="section-head" data-reveal="fade">
    <div>
      <span class="eyebrow">Latest Finds</span>
      <h2 class="section-title">Just added to the catalog</h2>
    </div>
  </div>
  <div class="grid-products grid-products--feature">{latest_cards}</div>
</section>
"""

    body = hero + trending_section + category_section + editorial_section + latest_section

    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site["siteName"],
        "url": site["url"],
        "logo": site["url"].rstrip("/") + "/assets/logo/wordmark.png",
        "description": site["description"],
    })
    # Entrance support (homepage only). The inline script runs before first
    # paint so the black overlay is already up -- no flash of the homepage --
    # and carries a timed failsafe so a JS failure can never leave the page
    # covered. Skipped for same-session returns (internal navigation home).
    intro_head = (
        '<script>(function(){try{var d=document.documentElement,s=location.search;'
        'var off=/[?&]intro=off/.test(s),forced=/[?&]intro=/.test(s);'
        'var seen=!forced&&sessionStorage.getItem("pf-intro-session")==="1";'
        'if(!off&&!seen){d.classList.add("intro-pending","intro-active");'
        'window.__pfFs=setTimeout(function(){d.classList.remove("intro-pending","intro-active")},7000)}'
        '}catch(e){}})();</script>'
        '<link rel="stylesheet" href="/css/intro.css" />'
        '<link rel="modulepreload" href="/js/components/introScene.js" />'
        '<link rel="preload" as="image" href="/assets/logo/wordmark.png" />'
    )
    extra_head = f'<script type="application/ld+json">{ld_json}</script>' + intro_head

    return base_page(
        site,
        title=f"{site['siteName']} — {site['tagline']}",
        description=site["description"],
        canonical_path="/",
        body_html=body,
        active_nav="home",
        page_scripts=["/js/pages/home.js"],
        extra_head=extra_head,
        show_intro=True,
    )


# --------------------------------------------------------------------------
# Category pages
# --------------------------------------------------------------------------

def render_category_page(site, category, all_categories, category_products):
    initial_sorted = sorted(category_products, key=lambda p: p.get("featured", False), reverse=True)
    cards = "".join(render_product_card(p, reveal=False, morph=True) for p in initial_sorted) if initial_sorted else ""

    empty_state = """
<div class="state-panel">
  <svg class="state-panel__icon" viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><path d="M4 7l1-3h14l1 3M4 7h16M4 7l1 13h14l1-13"/></svg>
  <p class="state-panel__title">Nothing published here yet</p>
  <p>New finds in this category are on the way — check back soon.</p>
</div>
"""

    body = f"""
<section class="page-hero category-hero">
  <div class="category-hero__watermark"><img src="/assets/images/categories/{category['slug']}.svg" alt="" /></div>
  <div class="container category-hero__content">
    {render_breadcrumbs([("Home", "/"), ("Categories", "/#categories"), (category['name'], None)])}
    <span class="eyebrow">Category</span>
    <h1 class="section-title" style="font-size: var(--fs-display-xl); view-transition-name: category-name-{category['slug']};">{esc(category['name'])}</h1>
    <p class="category-hero__desc">{esc(category['description'])}</p>
  </div>
</section>
<section class="section container">
  <div class="category-layout" data-category-app data-category-slug="{category['slug']}">
    <div class="category-filters" role="group" aria-label="Filter products">
      <div class="input-field" style="margin-bottom: var(--space-lg);">
        {SEARCH_ICON}
        <input type="search" placeholder="Search in {esc(category['name'])}…" data-category-search aria-label="Search in {esc(category['name'])}" autocomplete="off" enterkeyhint="search" spellcheck="false" />
      </div>
      <div class="filter-group" role="group" aria-labelledby="filter-rating-title">
        <h2 class="filter-group__title" id="filter-rating-title">Rating</h2>
        <div class="filter-chips">
          <button type="button" class="chip" data-filter-rating="4.5" aria-pressed="false">4.5+<span class="sr-only"> stars and up</span></button>
          <button type="button" class="chip" data-filter-rating="4" aria-pressed="false">4.0+<span class="sr-only"> stars and up</span></button>
          <button type="button" class="chip" data-filter-rating="3.5" aria-pressed="false">3.5+<span class="sr-only"> stars and up</span></button>
        </div>
      </div>
      <div class="filter-group" role="group" aria-labelledby="filter-price-title">
        <h2 class="filter-group__title" id="filter-price-title">Price</h2>
        <div class="filter-price">
          <div class="input-field"><input type="number" min="0" step="any" inputmode="decimal" autocomplete="off" placeholder="Min" data-filter-min-price aria-label="Minimum price in US dollars" /></div>
          <div class="input-field"><input type="number" min="0" step="any" inputmode="decimal" autocomplete="off" placeholder="Max" data-filter-max-price aria-label="Maximum price in US dollars" /></div>
        </div>
      </div>
      <div class="filter-group" role="group" aria-labelledby="filter-show-title">
        <h2 class="filter-group__title" id="filter-show-title">Show only</h2>
        <label class="filter-checkbox"><input type="checkbox" data-filter-featured /> Featured</label>
        <label class="filter-checkbox"><input type="checkbox" data-filter-trending /> Trending</label>
      </div>
      <button type="button" class="btn btn--secondary btn--sm btn--full" data-filters-clear>Clear filters</button>
    </div>
    <div>
      <div class="toolbar">
        <span class="toolbar__count" data-result-count role="status" aria-live="polite">{len(initial_sorted)} {'find' if len(initial_sorted) == 1 else 'finds'}</span>
        <div class="toolbar__controls">
          <div class="input-field select-field">
            <select data-sort-select aria-label="Sort products">
              <option value="featured">Featured</option>
              <option value="trending">Trending</option>
              <option value="newest">Newest</option>
              <option value="price-asc">Price: Low to High</option>
              <option value="price-desc">Price: High to Low</option>
              <option value="rating">Rating</option>
            </select>
          </div>
        </div>
      </div>
      {render_affiliate_note(site)}
      <div class="grid-products grid-products--feature" data-category-grid>{cards if cards else ''}</div>
      {'' if cards else empty_state}
    </div>
  </div>
</section>
"""

    return base_page(
        site,
        title=f"{category['name']} — {site['siteName']}",
        description=category["description"],
        canonical_path=f"/category/{category['slug']}/",
        og_image=f"/assets/images/categories/{category['slug']}.svg",
        body_html=body,
        page_scripts=["/js/pages/category.js"],
    )


# --------------------------------------------------------------------------
# Product detail pages
# --------------------------------------------------------------------------

def render_product_page(site, product, category, related_products):
    images = [product["image"]] + product.get("additionalImages", [])
    thumbs_html = ""
    if len(images) > 1:
        thumbs = "".join(
            f'<button type="button" class="product-detail__thumb{" is-active" if i == 0 else ""}" '
            f'data-gallery-thumb data-full-src="{img}" aria-pressed="{"true" if i == 0 else "false"}" '
            f'aria-label="Show photo {i+1} of {len(images)}"><img src="{img}" alt="" loading="lazy" width="72" height="72" /></button>'
            for i, img in enumerate(images)
        )
        thumbs_html = f'<div class="product-detail__thumbs">{thumbs}</div>'

    highlights = "".join(
        f'<li><svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 10l4 4 8-9"/></svg><span>{esc(h)}</span></li>'
        for h in product.get("highlights", [])
    )
    tags = "".join(f'<span class="tag-pill">{esc(t)}</span>' for t in product.get("tags", []))

    related_section = ""
    if related_products:
        related_items = "".join(
            f'<div class="rail__item">{render_product_card(p, reveal=False, morph=True)}</div>' for p in related_products
        )
        related_section = f"""
<section class="section">
  <div class="container section-head--split" data-reveal="fade">
    <div><span class="eyebrow">You Might Also Like</span><h2 class="section-title">More from {esc(category['name'])}</h2></div>
    <div class="rail-controls">
      <button class="icon-btn" type="button" data-rail-prev="related-rail" aria-label="Scroll back">{CHEVRON_LEFT_ICON}</button>
      <button class="icon-btn" type="button" data-rail-next="related-rail" aria-label="Scroll forward">{CHEVRON_ICON}</button>
    </div>
  </div>
  <div class="container">
    <div class="rail" id="related-rail" data-rail>{related_items}</div>
  </div>
</section>
"""

    body = f"""
<section class="section container" data-product-app data-product-slug="{product['slug']}">
  {render_breadcrumbs([("Home", "/"), (category['name'], f"/category/{category['slug']}/"), (product['name'], None)])}
  <div class="product-detail">
    <div class="product-detail__gallery pd-gallery-enter">
      <div class="product-detail__gallery-main"><img src="{product['image']}" alt="{esc(product['name'])}" data-gallery-main loading="eager" style="view-transition-name: product-photo-{product['slug']}" /></div>
      {thumbs_html}
    </div>
    <div>
      <div class="pd-enter pd-enter--1">
        <span class="product-detail__index tag-mono">{product_index_label(product)}</span>
        <span class="product-detail__category">{esc(category_label(product['category']))}{' · ' + esc(product['subcategory']) if product.get('subcategory') else ''}</span>
      </div>
      <h1 class="product-detail__title pd-enter pd-enter--2">{esc(product['name'])}</h1>
      <div class="product-detail__meta-row pd-enter pd-enter--3">
        <span class="product-detail__price">{format_price(product['price'], product['currency'])}</span>
        {render_stars(product['rating'], product['reviewCount'])}
        {'<span class="badge badge--gold">Trending</span>' if product.get('trending') else ''}
      </div>
      <div class="pd-enter pd-enter--4">
        <h2 class="sr-only">About this product</h2>
        <p class="product-detail__desc">{esc(product['description'])}</p>
        <div class="why-we-like-it">
          <div class="why-we-like-it__label">Why We Like It</div>
          <p>{esc(product['whyWeLikeIt'])}</p>
        </div>
        <h2 class="sr-only">Highlights</h2>
        <ul class="highlights-list">{highlights}</ul>
        <div class="tag-row">{tags}</div>
      </div>
      <div class="cta-panel pd-enter pd-enter--5">
        <a class="btn btn--primary btn--full" data-affiliate-link data-product-slug="{product['slug']}" aria-label="View at Amazon: {esc(product['name'])} (opens in a new tab)">View at Amazon {CHEVRON_ICON}</a>
        <p class="cta-panel__disclaimer">You will leave {esc(site['siteName'])} to view this product on Amazon, where you can check the current price, availability and shipping before you buy. This is an affiliate link: {esc(site['siteName'])} may earn a commission from qualifying purchases, at no extra cost to you. <a href="/affiliate-disclosure.html">Affiliate disclosure</a>.</p>
      </div>
    </div>
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
        "brand": {"@type": "Brand", "name": site["siteName"]},
    }
    if product.get("price") is not None:
        ld_json["offers"] = {
            "@type": "Offer",
            "price": product["price"],
            "priceCurrency": product["currency"],
            "availability": "https://schema.org/InStock",
            "url": product.get("externalUrl") or "",
        }
    if product.get("rating") and product.get("reviewCount"):
        ld_json["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": product["rating"],
            "reviewCount": product["reviewCount"],
        }
    extra_head = f'<script type="application/ld+json">{json.dumps(ld_json)}</script>'

    return base_page(
        site,
        title=f"{product['name']} — {site['siteName']}",
        description=product["shortDescription"],
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
    body = f"""
<section class="page-hero container">
  {render_breadcrumbs([("Home", "/"), ("About", None)])}
  <span class="eyebrow">About</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">We find the interesting stuff first.</h1>
  <p class="about-hero__lede">PRIME.FINDS discovers interesting products, useful gadgets, stylish items, and things worth knowing about — then saves you the hours it'd take to find them yourself.</p>
</section>
<section class="section container narrow">
  <div class="prose">
    <p>Somewhere between "I need this" and "I'll never find it" is where PRIME.FINDS lives. We look through the endless stream of new products so you don't have to — filtering out the noise, the gimmicks, and the things that look good in a thumbnail but fall apart in real use.</p>
    <p>We're not a marketplace and we don't manufacture anything. When something earns a spot here, we point you to where you can actually get it. That's the whole model: discovery first, honestly presented, no pressure to buy.</p>
  </div>
  <hr class="hr" />
  <div class="value-grid">
    <div data-reveal>
      <div class="value-item__num">01</div>
      <div class="value-item__title">Curated, not crowdsourced</div>
      <div class="value-item__desc">Every product here was chosen on purpose — not auto-imported from a feed.</div>
    </div>
    <div data-reveal>
      <div class="value-item__num">02</div>
      <div class="value-item__title">Built for a quick look</div>
      <div class="value-item__desc">Come from a reel, see something good, move on. No account required, no friction.</div>
    </div>
    <div data-reveal>
      <div class="value-item__num">03</div>
      <div class="value-item__title">Honest about the model</div>
      <div class="value-item__desc">We may earn a commission on some links. It never decides what gets featured. <a href="/affiliate-disclosure.html">Read the affiliate disclosure</a>.</div>
    </div>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"About — {site['siteName']}",
        description="PRIME.FINDS curates interesting, useful, and stylish products so you don't have to spend hours searching for them yourself.",
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
  {render_breadcrumbs([("Home", "/"), (title, None)])}
  <span class="eyebrow">{esc(eyebrow)}</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">{esc(title)}</h1>
  <p class="legal-updated">Last updated: <time datetime="{updated}">{format_date_long(updated)}</time></p>
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
        title=f"{title} — {site['siteName']}",
        description=description,
        canonical_path=f"/{slug}",
        body_html=body,
    )


def render_accessibility_page(site):
    d = format_date_long(site["legalUpdated"])
    lead = (
        "<p>PRIME.FINDS wants everyone to be able to browse the catalog, whether they use a keyboard, a screen reader, "
        "magnification, voice control or a touch screen. We treat accessibility as ongoing work, not something that is "
        "finished once.</p>"
    )
    sections = f"""
    <h2>The standard we are working toward</h2>
    <p>We are working toward conformance with the Web Content Accessibility Guidelines (WCAG) 2.2 at Level AA, published by the World Wide Web Consortium (W3C).</p>

    <h2>Current status</h2>
    <p>PRIME.FINDS has not been independently audited or certified, and we do not claim that it fully conforms to WCAG 2.2 Level AA. What we can say accurately is this: on {d} we reviewed the homepage, category pages, product pages, search, the site menu, filters, the entrance animation and the legal pages, and fixed the problems that review found. The review used:</p>
    <ul>
      <li>automated checks with the axe-core testing engine;</li>
      <li>measured colour-contrast checks of text and interface components;</li>
      <li>keyboard testing of tab order and visible focus, and of the Escape key and where focus lands after menus and dialogs close;</li>
      <li>text enlarged to 175% and pages narrowed to a 320-pixel-wide screen, to check that nothing is cut off and nothing forces sideways scrolling;</li>
      <li>checks of the entrance animation and the rest of the interface with the Reduce motion option switched on, and with the high-contrast option switched on.</li>
    </ul>
    <p>We have not yet tested with dedicated screen readers (such as NVDA, JAWS or VoiceOver), or with disabled users, so problems may remain that this kind of testing would reveal.</p>

    <h2>What we have done</h2>
    <ul>
      <li>A "Skip to main content" link at the start of every page.</li>
      <li>Every feature can be used with a keyboard, with visible focus outlines. The site menu, search and accessibility options open as dialogs that take focus, keep it inside while open, close with the Escape key, and return focus to the control that opened them.</li>
      <li>Standard HTML headings, lists, landmarks, buttons and links. Product links are named after the product. Each "View at Amazon" button names the product it is for and says that it opens in a new tab.</li>
      <li>Product photos have text alternatives that name the product. Purely decorative artwork is hidden from screen readers.</li>
      <li>Search results, and the number of products left after you filter, are announced to screen readers. Filter buttons say whether they are switched on.</li>
      <li>Text and interface colours were checked against the WCAG contrast minimums, and the pale gray text used for small captions was darkened to pass.</li>
      <li>Layouts adapt down to 320 CSS pixels wide and to enlarged text, and browser zoom is never disabled.</li>
      <li>Animation respects your device's reduced-motion setting, the site's content never depends on animation, and nothing in it flashes.</li>
    </ul>

    <h2>Accessibility options on this site</h2>
    <p>The <strong>Accessibility options</strong> button in the page header (a circle with a person in it) opens a small panel with:</p>
    <ul>
      <li><strong>Text size:</strong> five steps, from the standard size up to 175%.</li>
      <li><strong>High contrast:</strong> black text on white with stronger borders and focus outlines.</li>
      <li><strong>Reduce motion:</strong> turns off transitions and the card tilt effect, and replaces the entrance animation with a simple fade.</li>
      <li><strong>Reset all:</strong> returns everything to the defaults.</li>
    </ul>
    <p>Your choices are saved only in your own browser (see the <a href="/cookie-notice.html">Cookie Notice</a>); they are not sent to PRIME.FINDS or anyone else. These options add to, and do not replace, your browser's and device's own accessibility settings, which the site also respects. The site itself is built to be usable without them.</p>

    <h2>The entrance animation</h2>
    <p>The homepage opens with a short animated introduction: about four seconds on a first visit and shorter on later visits. It plays once per browsing session. You can skip it at any moment by pressing any key, clicking or tapping, or using the <strong>Skip intro</strong> button, and there is an Accessibility link on top of it so this page can be reached before you enter the site. If your device is set to reduce motion, or you switch on Reduce motion, you get a simple fade instead of the full animation. The animation does not contain flashing content and the site's content does not depend on it. We have not measured it with a dedicated photosensitivity analysis tool.</p>

    <h2>Known limitations</h2>
    <ul>
      <li>Some product photos come from the retailer's listing and contain text or graphics inside the image, such as slogans or feature callouts. The photo's text alternative names the product, and the product description on the page carries the key details, but not everything shown inside an image is described.</li>
      <li>The "View at Amazon" buttons receive their destination through a script after the page loads. If scripts are blocked or fail, those buttons will not work.</li>
      <li>When you follow a link to Amazon or another retailer you leave PRIME.FINDS. The accessibility of those sites is outside our control.</li>
      <li>The site loads its fonts from Google Fonts. If they are blocked, a fallback font is used and the text may look different.</li>
      <li>The site is available in English only.</li>
      <li>We have not yet tested with screen readers or with disabled users, as explained above.</li>
      <li>Some effects, such as product cards tilting under the pointer, are pointer-only enhancements. They do not hide any information, and Reduce motion turns them off.</li>
    </ul>

    <h2 id="report">Report a barrier or ask for help</h2>
    <p>If something on PRIME.FINDS is hard or impossible for you to use, or you need information from the site in a different form, please tell us. It helps to include the address of the page, what you were trying to do, what went wrong, and the browser and any assistive technology you use.</p>
    {render_contact_paragraph(site)}
    <p>We read reports as they come in and give priority to barriers that stop someone from finding a product or reaching a retailer. We cannot promise a specific response time. If you are not satisfied with how a concern is handled, you may be able to raise it with an accessibility or consumer authority in your own country.</p>

    <h2>Technical information</h2>
    <p>PRIME.FINDS is built with HTML, CSS and JavaScript, with WAI-ARIA used only where standard HTML does not give the right meaning. It is designed for current versions of the major desktop and mobile browsers.</p>

    <h2>Review date</h2>
    <p>This statement was last reviewed on <time datetime="{site['legalUpdated']}">{d}</time> and will be updated as the site changes and as we learn more.</p>
"""
    return render_legal_page(
        site,
        eyebrow="Accessibility",
        title="Accessibility Statement",
        slug="accessibility.html",
        description="How PRIME.FINDS approaches accessibility, what has been tested, known limitations, and how to report a barrier.",
        lead_html=lead,
        sections_html=sections,
    )


def render_cookie_page(site):
    lead = (
        "<p>This page explains what PRIME.FINDS stores on your device and which third parties are involved when you use the site.</p>"
    )
    sections = f"""
    <h2>The short version</h2>
    <p>PRIME.FINDS does not set cookies of its own, and it does not use advertising or analytics cookies or trackers. It keeps a few small preferences in your browser's storage. Because there are no non-essential cookies, the site does not show a cookie-consent banner. If that changes, this notice will be updated first and choices will be offered where required.</p>

    <h2>What PRIME.FINDS stores in your browser</h2>
    <dl class="legal-list">
      <dt><code>pf-visited</code> &middot; local storage</dt>
      <dd>Remembers that you have seen the entrance animation, so returning visitors get a shorter version. It stays until you clear your browser data.</dd>
      <dt><code>pf-intro-session</code> &middot; session storage</dt>
      <dd>Stops the entrance animation replaying while you move around the site in the same browsing session. It is cleared when you close the tab.</dd>
      <dt><code>pf-a11y</code> &middot; local storage</dt>
      <dd>Remembers your accessibility choices (text size, high contrast, reduce motion). It is created only if you change one of them, and removed when you use Reset all or clear your browser data.</dd>
    </dl>
    <p>None of these is sent to PRIME.FINDS or to any third party.</p>

    <h2>Third parties</h2>
    <ul>
      <li><strong>Google Fonts.</strong> The site's fonts are loaded from Google's servers (fonts.googleapis.com and fonts.gstatic.com). Requests to those servers necessarily include your IP address and browser details. See Google's own privacy information for how it handles them.</li>
      <li><strong>GitHub Pages.</strong> The site is hosted by GitHub Pages. As with any web host, GitHub receives standard request information (such as your IP address) when a page loads. See GitHub's privacy statement.</li>
      <li><strong>Amazon and other retailers.</strong> When you click a link to a retailer you leave PRIME.FINDS. Retailers and affiliate programs may use cookies and similar technologies, including to record that a purchase came from PRIME.FINDS. Those are governed by their own cookie policies.</li>
    </ul>

    <h2>Managing your data</h2>
    <p>You can clear the items above in your browser's settings, or use <strong>Reset all</strong> in the accessibility options to remove <code>pf-a11y</code>. Most browsers can also block third-party requests and cookies; if the Google Fonts requests are blocked, the site falls back to your system fonts.</p>
    {render_contact_paragraph(site, "Questions about this notice? ")}
"""
    return render_legal_page(
        site,
        eyebrow="Legal",
        title="Cookie Notice",
        slug="cookie-notice.html",
        description="What PRIME.FINDS stores in your browser, and the third parties involved when you use the site.",
        lead_html=lead,
        sections_html=sections,
    )


def render_affiliate_disclosure_page(site):
    extra = site.get("affiliateStatement", "").strip()
    extra_html = f"<p>{esc(extra)}</p>" if extra else ""
    lead = (
        '<div class="callout"><p><strong>In short:</strong> many links on PRIME.FINDS, including the &ldquo;View at Amazon&rdquo; buttons, '
        "are affiliate links. If you buy through them, PRIME.FINDS may earn a commission from qualifying purchases, "
        "at no extra cost to you.</p></div>"
    )
    sections = f"""
    {extra_html}
    <h2>What PRIME.FINDS is</h2>
    <p>PRIME.FINDS is an independent product-discovery website. We choose products we think are interesting, useful or well made, describe them, and link to the retailer, mostly Amazon, where you can buy them.</p>

    <h2>How the links work</h2>
    <p>When you select &ldquo;View at Amazon&rdquo;, you leave PRIME.FINDS and land on Amazon, sometimes after passing through a short link such as <code>link.amazon</code> or <code>amzn.to</code>. Amazon may use cookies or similar technology to record that you came from PRIME.FINDS. If you then buy, PRIME.FINDS may earn a commission under the terms of the affiliate program. You pay the same price either way.</p>

    <h2>What happens on the retailer's site</h2>
    <p>PRIME.FINDS does not sell anything and does not process your purchase. Payment, delivery, returns, warranty and customer service are handled entirely by Amazon or whichever retailer you buy from, under their terms. We never see your payment details or your order.</p>

    <h2>What this does not change</h2>
    <p>Products are chosen because we think they are worth knowing about, not because of the commission they may generate. Whether a link earns money has no bearing on whether a product is featured, and it does not change the price you pay. PRIME.FINDS is independent and is not endorsed by, sponsored by or affiliated with Amazon or any brand mentioned on the site, unless a page says so explicitly.</p>

    <h2>Prices, ratings and product details</h2>
    <p>Prices, availability, specifications, shipping options and reviews on retailer sites change, and sellers can change or withdraw a listing at any time. Where a price is shown as &ldquo;Check price&rdquo;, we do not display one because it varies by location, seller or option. Star ratings and review counts shown on PRIME.FINDS come from the retailer's listing when the product was added and may no longer match. Please check the current details on the retailer's website before you buy.</p>

    <h2>Other programs</h2>
    <p>If PRIME.FINDS joins other affiliate programs, this page will be updated to say so.</p>
    {render_contact_paragraph(site, "Questions about a link or this disclosure? ")}
"""
    return render_legal_page(
        site,
        eyebrow="Legal",
        title="Affiliate Disclosure",
        slug="affiliate-disclosure.html",
        description="How PRIME.FINDS uses affiliate links, what happens when you click one, and what it does and does not change.",
        lead_html=lead,
        sections_html=sections,
    )


def render_privacy_page(site):
    lead = (
        "<p>PRIME.FINDS is a product-discovery website that is designed to collect as little about you as possible. "
        "This page explains, in plain language, what that means in practice.</p>"
    )
    sections = f"""
    <h2>Who is responsible</h2>
    <p>PRIME.FINDS is an independent website. It does not currently publish a company name or postal address. For questions about this policy, use the contact options at the end of this page.</p>

    <h2>What PRIME.FINDS collects</h2>
    <ul>
      <li><strong>Nothing directly from you.</strong> There are no accounts, sign-ups, comment forms, newsletters or payment forms, so PRIME.FINDS does not ask for or store your name, email address or payment details.</li>
      <li><strong>Searches and filters stay in your browser.</strong> The search box and filters work on data your browser has already loaded; what you type is not sent to PRIME.FINDS.</li>
      <li><strong>No analytics or advertising trackers.</strong> The site's code includes a switched-off analytics hook, but no analytics or advertising service is running. If that changes, this policy will be updated first.</li>
      <li><strong>Small preferences on your device.</strong> The site keeps a few items in your browser's storage (whether you have seen the entrance animation, and your accessibility choices). They stay on your device. The <a href="/cookie-notice.html">Cookie Notice</a> lists each one.</li>
    </ul>

    <h2>Third parties involved when you use the site</h2>
    <ul>
      <li><strong>GitHub Pages</strong> hosts the site. As with any web host, GitHub receives standard request information, such as your IP address and browser details, when a page loads, and may log it. PRIME.FINDS does not use that data. See GitHub's privacy statement.</li>
      <li><strong>Google Fonts</strong> supplies the site's typefaces. Your browser requests them from Google's servers, so Google receives your IP address and browser details. See Google's privacy information.</li>
      <li><strong>Amazon and other retailers.</strong> When you select a &ldquo;View at Amazon&rdquo; or similar button you leave PRIME.FINDS. The retailer, and any link shortener or affiliate program involved, handles your data under its own policies, and may use cookies to attribute a purchase to PRIME.FINDS. We do not receive your account, order or payment details.</li>
    </ul>

    <h2>Children</h2>
    <p>PRIME.FINDS is not directed at children, and it does not knowingly collect personal information from anyone, including children.</p>

    <h2>Visitors from different countries</h2>
    <p>PRIME.FINDS can be visited from anywhere, and data-protection rules differ from country to country. Because PRIME.FINDS does not collect personal information directly, most of the rights you may have over your data relate to the third parties above rather than to PRIME.FINDS. If you have a question or request about anything PRIME.FINDS itself might hold, please get in touch and we will look into it.</p>

    <h2>Your choices</h2>
    <p>You can clear the items PRIME.FINDS stores in your browser at any time, block third-party requests in your browser settings (the site will fall back to system fonts), or simply not follow the links to retailers.</p>

    <h2>Changes to this policy</h2>
    <p>If PRIME.FINDS starts collecting anything new, such as introducing analytics or an account system, this page will be updated before that happens, and the date at the top will change.</p>

    <h2>Contact</h2>
    {render_contact_paragraph(site)}
"""
    return render_legal_page(
        site,
        eyebrow="Legal",
        title="Privacy Policy",
        slug="privacy-policy.html",
        description="What PRIME.FINDS collects (very little), the third parties involved when you use the site, and your choices.",
        lead_html=lead,
        sections_html=sections,
    )


def render_terms_page(site):
    lead = (
        "<p>These terms describe how PRIME.FINDS may be used and what it is, and is not, responsible for. "
        "If you do not agree with them, please do not use the site.</p>"
    )
    sections = f"""
    <h2>What PRIME.FINDS is</h2>
    <p>PRIME.FINDS is an independent, editorial product-discovery website. It is not a store, a marketplace or a retailer. It does not sell products, take payments, ship goods, or handle returns, warranties or customer service. Any purchase is made on the retailer's own website, most often Amazon, and is a matter between you and that retailer.</p>

    <h2>Product information</h2>
    <p>Product names, descriptions, ratings, review counts, images and links on PRIME.FINDS are provided for information. Prices, availability, specifications, shipping, compatibility and reviews are set by retailers and sellers and can change or be withdrawn at any time without notice. Some prices are shown as &ldquo;Check price&rdquo; because they vary. We try to describe products accurately from the retailer's listing when we add them, but we cannot guarantee that everything shown is complete, correct or current. Always verify the details on the retailer's website before you buy.</p>

    <h2>Affiliate links</h2>
    <p>Many links on PRIME.FINDS are affiliate links, and PRIME.FINDS may earn a commission if you buy through them, at no extra cost to you. See the <a href="/affiliate-disclosure.html">Affiliate Disclosure</a>.</p>

    <h2>Third-party sites</h2>
    <p>Links take you to websites that PRIME.FINDS does not own or control. We are not responsible for their content, their policies, or their accessibility, and following a link is your choice.</p>

    <h2>Not professional advice</h2>
    <p>Content on PRIME.FINDS is general information and personal curation. It is not professional, safety, medical, financial or legal advice. Follow the manufacturer's instructions and warnings for any product you buy.</p>

    <h2>Content and ownership</h2>
    <p>The editorial writing, curation, design and the PRIME.FINDS name and logo belong to PRIME.FINDS. Product names, brands, trademarks and product images belong to their respective owners and are shown to identify the products being discussed. If you own rights in something on the site and believe it is being used incorrectly, please get in touch and we will look at it.</p>

    <h2>Using the site</h2>
    <p>Please use PRIME.FINDS in good faith: do not misuse it, interfere with how it works, or try to access it in ways it is not meant to be accessed.</p>

    <h2>Availability and liability</h2>
    <p>PRIME.FINDS is provided &ldquo;as is&rdquo;, without promises about uptime, accuracy or fitness for a particular purpose. To the extent the law allows, PRIME.FINDS is not responsible for losses that arise from decisions you make about products or retailers, or from problems with a retailer's site or service. Nothing in these terms limits any rights you have under the laws of your country that cannot be excluded or limited.</p>

    <h2>Changes to these terms</h2>
    <p>These terms may be updated as PRIME.FINDS changes. The date at the top shows when they were last revised.</p>

    <h2>Contact</h2>
    {render_contact_paragraph(site)}
"""
    return render_legal_page(
        site,
        eyebrow="Legal",
        title="Terms of Use",
        slug="terms.html",
        description="Terms of use for PRIME.FINDS: what the site is, how product information and affiliate links work, and its limits.",
        lead_html=lead,
        sections_html=sections,
    )


def render_404_page(site):
    body = """
<section class="container error-page">
  <div>
    <div class="error-page__code">404</div>
    <h1 class="section-title" style="margin-top: var(--space-sm);">This find is gone.</h1>
    <p class="section-desc" style="margin: var(--space-sm) auto var(--space-lg);">The page you're looking for doesn't exist or has moved.</p>
    <a class="btn btn--primary" href="/">Back to Homepage</a>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"Page Not Found — {site['siteName']}",
        description="This page doesn't exist or has moved.",
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
    write_file(os.path.join(PUBLIC_DIR, "data", "products.json"), json.dumps(published, indent=2))
    write_file(os.path.join(PUBLIC_DIR, "data", "categories.json"), json.dumps(categories, indent=2))

    # ---- Homepage ----
    write_file(os.path.join(PUBLIC_DIR, "index.html"), render_homepage(site, categories, published, counts))

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
        related = [p for p in published if p["category"] == product["category"] and p["slug"] != product["slug"]][:4]
        write_file(
            os.path.join(PUBLIC_DIR, "product", product["slug"], "index.html"),
            render_product_page(site, product, category, related),
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
    urls += [f"/category/{c['slug']}/" for c in categories]
    urls += [f"/product/{p['slug']}/" for p in published]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "".join(f"  <url><loc>{base_url}{u}</loc></url>\n" for u in urls)
    sitemap += "</urlset>\n"
    write_file(os.path.join(PUBLIC_DIR, "sitemap.xml"), sitemap)

    write_file(os.path.join(PUBLIC_DIR, "robots.txt"), f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n")

    manifest = {
        "name": site["siteName"],
        "short_name": site["siteName"].split(".")[0],
        "description": site["description"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0b",
        "theme_color": "#0a0a0b",
        "icons": [
            {"src": "/assets/logo/favicon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/logo/favicon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/assets/logo/maskable-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    write_file(os.path.join(PUBLIC_DIR, "site.webmanifest"), json.dumps(manifest, indent=2))

    print(f"Built {len(urls)} pages ({len(published)} products across {len(categories)} categories, "
          f"{len(products) - len(published)} unpublished/hidden).")


if __name__ == "__main__":
    main()
