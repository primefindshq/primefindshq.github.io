"""
PRIME.FINDS static site generator.

Stands in for what a Next.js `generateStaticParams` + `generateMetadata`
build step would do, without requiring Node.js on this machine. Reads the
"database" (data/*.json) and renders:

  - public/index.html                          (homepage)
  - public/category/<slug>/index.html          (one per category)
  - public/product/<slug>/index.html           (one per PUBLISHED product)
  - public/about.html, affiliate-disclosure.html, privacy-policy.html,
    terms.html, 404.html
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


# --------------------------------------------------------------------------
# Shared chrome: header, mobile menu, search overlay, footer
# --------------------------------------------------------------------------

SEARCH_ICON = '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="9" cy="9" r="6.5"/><path d="M18 18l-3.8-3.8"/></svg>'
CLOSE_ICON = '<svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg>'
INSTAGRAM_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1"/></svg>'
CHEVRON_ICON = '<svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 5l6 5-6 5"/></svg>'


def render_header(site, active=None):
    nav_items = "".join(
        f'<li><a class="main-nav__link{" is-active" if active == link["label"].lower() else ""}" href="{link["href"]}">{esc(link["label"])}</a></li>'
        for link in site["navLinks"]
    )
    return f"""
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="site-header">
  <div class="container site-header__inner">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])} home">
      <img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1075" height="580" />
    </a>
    <nav class="main-nav" aria-label="Primary">
      <ul class="main-nav__list">{nav_items}</ul>
    </nav>
    <div class="header-actions">
      <button class="icon-btn" type="button" data-search-open aria-label="Search products">{SEARCH_ICON}</button>
      <button class="hamburger-btn" type="button" data-menu-toggle aria-expanded="false" aria-controls="mobile-menu" aria-label="Open menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
"""


def render_mobile_menu(site):
    links = "".join(
        f'<li><a class="mobile-menu__link" href="{link["href"]}">{esc(link["label"])}</a></li>'
        for link in site["navLinks"]
    )
    return f"""
<div class="mobile-menu" id="mobile-menu" data-mobile-menu>
  <div class="mobile-menu__top">
    <a class="brand-logo" href="/" aria-label="{esc(site['siteName'])} home"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1075" height="580" /></a>
    <button class="icon-btn" type="button" data-menu-close aria-label="Close menu">{CLOSE_ICON}</button>
  </div>
  <ul class="mobile-menu__list">{links}</ul>
  <p class="mobile-menu__footer">{esc(site['tagline'])}</p>
</div>
"""


def render_search_overlay():
    return f"""
<div class="search-overlay" data-search-overlay role="dialog" aria-modal="true" aria-label="Search products">
  <div class="search-overlay__panel">
    <div class="search-overlay__input-row">
      {SEARCH_ICON}
      <input class="search-overlay__input" type="search" placeholder="Search products, categories, tags…" data-search-input aria-label="Search products" />
      <button class="icon-btn" type="button" data-search-close aria-label="Close search">{CLOSE_ICON}</button>
    </div>
    <div data-search-results></div>
  </div>
</div>
"""


def render_footer(site):
    categories_links = "".join(
        f'<li><a href="/category/{c["slug"]}/">{esc(c["name"])}</a></li>' for c in _ALL_CATEGORIES
    )
    nav_links = "".join(f'<li><a href="{l["href"]}">{esc(l["label"])}</a></li>' for l in site["navLinks"])
    legal_links = "".join(f'<li><a href="{l["href"]}">{esc(l["label"])}</a></li>' for l in site["footerLegalLinks"])
    instagram = site["social"].get("instagram", "")
    social_html = (
        f'<a href="{esc(instagram)}" target="_blank" rel="noopener" aria-label="PRIME.FINDS on Instagram">{INSTAGRAM_ICON}</a>'
        if instagram
        else f'<span aria-disabled="true" title="Instagram — coming soon">{INSTAGRAM_ICON}</span>'
    )
    year = "2026"
    return f"""
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand-logo" href="/"><img src="/assets/logo/wordmark.png" alt="{esc(site['siteName'])}" width="1075" height="580" /></a>
        <p class="footer-brand__tagline">{esc(site['tagline'])}</p>
      </div>
      <div>
        <h3 class="footer-heading">Explore</h3>
        <ul class="footer-links">{nav_links}</ul>
      </div>
      <div>
        <h3 class="footer-heading">Categories</h3>
        <ul class="footer-links">{categories_links}</ul>
      </div>
      <div>
        <h3 class="footer-heading">Legal</h3>
        <ul class="footer-links">{legal_links}</ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; {year} {esc(site['siteName'])}. All rights reserved.</span>
      <div class="footer-social">{social_html}</div>
    </div>
  </div>
</footer>
"""


# --------------------------------------------------------------------------
# Product / category card markup (SSR mirror of the JS components)
# --------------------------------------------------------------------------

def render_product_card(product, reveal=True):
    badges = ""
    if product.get("trending"):
        badges += '<span class="badge badge--gold">Trending</span>'
    if product.get("featured"):
        badges += '<span class="badge badge--outline-gold">Featured</span>'
    reveal_attr = "data-reveal" if reveal else ""
    return f"""
<article class="product-card" {reveal_attr}>
  <a class="product-card-link" href="/product/{product['slug']}/" aria-label="View {esc(product['name'])}">
    <div class="product-card__media">
      <div class="product-card__badges">{badges}</div>
      <img src="{product['image']}" alt="{esc(product['name'])}" loading="lazy" width="800" height="800"
           onerror="this.onerror=null;this.src='/assets/images/fallback.svg';" />
    </div>
    <div class="product-card__body">
      <span class="product-card__category">{esc(category_label(product['category']))}</span>
      <h3 class="product-card__name">{esc(product['name'])}</h3>
      <p class="product-card__desc visually-line-clamp-2">{esc(product['shortDescription'])}</p>
      <div class="product-card__meta">
        <span class="product-card__price">{format_price(product['price'], product['currency'])}</span>
        {render_stars(product['rating'], product['reviewCount'])}
      </div>
    </div>
  </a>
  <div class="product-card__cta">
    <span>View details</span>
    <a class="btn--ghost" data-affiliate-link data-product-slug="{product['slug']}">View Product {CHEVRON_ICON}</a>
  </div>
</article>
"""


def render_category_card(category, count):
    return f"""
<a class="category-card" href="/category/{category['slug']}/" data-reveal>
  <div class="category-card__media"><img src="/assets/images/categories/{category['slug']}.svg" alt="" loading="lazy" width="1200" height="900" /></div>
  <div class="category-card__body">
    <h3 class="category-card__name">{esc(category['name'])}</h3>
    <p class="category-card__desc">{esc(category['shortDescription'])}</p>
    <span class="category-card__count">{count} {'find' if count == 1 else 'finds'}</span>
  </div>
</a>
"""


# --------------------------------------------------------------------------
# Base HTML document
# --------------------------------------------------------------------------

def base_page(site, *, title, description, canonical_path, og_image=None, body_html, active_nav=None, page_scripts=None, extra_head=""):
    css_links = "\n  ".join(f'<link rel="stylesheet" href="{href}" />' for href in CSS_FILES)
    canonical_url = site["url"].rstrip("/") + canonical_path
    og_image_url = site["url"].rstrip("/") + (og_image or "/assets/logo/og-image.jpg")
    scripts = "".join(f'<script type="module" src="{s}"></script>' for s in (page_scripts or []))

    return f"""<!doctype html>
<html lang="{site.get('locale', 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{canonical_url}" />
  <link rel="icon" href="/assets/logo/favicon.ico" sizes="any" />
  <link rel="icon" href="/assets/logo/favicon-32.png" type="image/png" sizes="32x32" />
  <link rel="icon" href="/assets/logo/favicon-192.png" type="image/png" sizes="192x192" />
  <link rel="apple-touch-icon" href="/assets/logo/apple-touch-icon.png" />
  <link rel="manifest" href="/site.webmanifest" />
  <meta name="theme-color" content="#0a0a0b" />

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
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap" />
  {css_links}
  {extra_head}
</head>
<body>
  {render_header(site, active_nav)}
  {render_mobile_menu(site)}
  {render_search_overlay()}
  <main id="main-content">
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
    trending = [p for p in products if p.get("trending")][:8]
    latest = sorted(products, key=lambda p: p["createdAt"], reverse=True)[:8]
    featured = next((p for p in products if p.get("featured")), products[0] if products else None)

    hero = f"""
<section class="hero">
  <div class="hero__bg"><img src="/assets/images/hero/hero.svg" alt="" /></div>
  <div class="container hero__content">
    <span class="hero__eyebrow entrance-mark"><img src="/assets/logo/mark.png" alt="" width="374" height="419" style="height:18px;width:auto;" /> {esc(site['siteName'])}</span>
    <h1 class="hero__title entrance-headline">DISCOVER WHAT'S <span class="accent">WORTH BUYING.</span></h1>
    <p class="hero__sub entrance-sub">Curated products. Smart finds. No endless searching.</p>
    <div class="hero__ctas entrance-cta">
      <a class="btn btn--primary" href="#trending">Explore Finds</a>
      <a class="btn btn--secondary" href="#categories">Explore Categories</a>
    </div>
  </div>
</section>
"""

    trending_cards = "".join(render_product_card(p) for p in trending)
    trending_section = f"""
<section class="section container" id="trending">
  <div class="section-head">
    <div>
      <span class="eyebrow">Trending Now</span>
      <h2 class="section-title">What everyone's clicking on</h2>
    </div>
  </div>
  <div class="grid-products">{trending_cards}</div>
</section>
"""

    category_cards = "".join(render_category_card(c, counts.get(c["slug"], 0)) for c in categories)
    category_section = f"""
<section class="section container" id="categories">
  <div class="section-head">
    <div>
      <span class="eyebrow">Browse</span>
      <h2 class="section-title">Shop by category</h2>
      <p class="section-desc">Seven ways into the catalog — more get added as we curate more.</p>
    </div>
  </div>
  <div class="grid-categories">{category_cards}</div>
</section>
"""

    latest_cards = "".join(render_product_card(p) for p in latest)
    latest_section = f"""
<section class="section container" id="latest">
  <div class="section-head">
    <div>
      <span class="eyebrow">Latest Finds</span>
      <h2 class="section-title">Just added</h2>
    </div>
  </div>
  <div class="grid-products">{latest_cards}</div>
</section>
"""

    featured_section = ""
    if featured:
        featured_section = f"""
<section class="section container">
  <div class="featured-product" data-reveal>
    <div class="featured-product__media"><img src="{featured['image']}" alt="{esc(featured['name'])}" loading="lazy" /></div>
    <div class="featured-product__text">
      <span class="featured-product__label">Featured Find</span>
      <h2 class="featured-product__title">{esc(featured['name'])}</h2>
      <p class="featured-product__desc">{esc(featured['whyWeLikeIt'])}</p>
      <div class="featured-product__price">{format_price(featured['price'], featured['currency'])}</div>
      <a class="btn btn--primary" href="/product/{featured['slug']}/">View Product {CHEVRON_ICON}</a>
    </div>
  </div>
</section>
"""

    body = hero + trending_section + category_section + latest_section + featured_section

    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site["siteName"],
        "url": site["url"],
        "logo": site["url"].rstrip("/") + "/assets/logo/wordmark.png",
        "description": site["description"],
    })
    extra_head = f'<script type="application/ld+json">{ld_json}</script>'

    return base_page(
        site,
        title=f"{site['siteName']} — {site['tagline']}",
        description=site["description"],
        canonical_path="/",
        body_html=body,
        active_nav="home",
        page_scripts=["/js/pages/home.js"],
        extra_head=extra_head,
    )


# --------------------------------------------------------------------------
# Category pages
# --------------------------------------------------------------------------

def render_category_page(site, category, all_categories, category_products):
    initial_sorted = sorted(category_products, key=lambda p: p.get("featured", False), reverse=True)
    cards = "".join(render_product_card(p, reveal=False) for p in initial_sorted) if initial_sorted else ""

    empty_state = """
<div class="state-panel">
  <svg class="state-panel__icon" viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><path d="M4 7l1-3h14l1 3M4 7h16M4 7l1 13h14l1-13"/></svg>
  <p class="state-panel__title">Nothing published here yet</p>
  <p>New finds in this category are on the way — check back soon.</p>
</div>
"""

    body = f"""
<section class="page-hero container">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">/</span><a href="/#categories">Categories</a><span class="sep">/</span><span aria-current="page">{esc(category['name'])}</span></nav>
  <span class="eyebrow">Category</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">{esc(category['name'])}</h1>
  <p class="category-hero__desc">{esc(category['description'])}</p>
</section>
<section class="section container">
  <div class="category-layout" data-category-app data-category-slug="{category['slug']}">
    <aside class="category-filters">
      <div class="input-field" style="margin-bottom: var(--space-lg);">
        {SEARCH_ICON}
        <input type="search" placeholder="Search in {esc(category['name'])}…" data-category-search aria-label="Search in {esc(category['name'])}" />
      </div>
      <div class="filter-group">
        <h3 class="filter-group__title">Rating</h3>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
          <button type="button" class="chip" data-filter-rating="4.5">4.5+</button>
          <button type="button" class="chip" data-filter-rating="4">4.0+</button>
          <button type="button" class="chip" data-filter-rating="3.5">3.5+</button>
        </div>
      </div>
      <div class="filter-group">
        <h3 class="filter-group__title">Price</h3>
        <div style="display:flex; gap:8px;">
          <div class="input-field"><input type="number" min="0" placeholder="Min" data-filter-min-price aria-label="Minimum price" /></div>
          <div class="input-field"><input type="number" min="0" placeholder="Max" data-filter-max-price aria-label="Maximum price" /></div>
        </div>
      </div>
      <div class="filter-group">
        <h3 class="filter-group__title">Show only</h3>
        <label class="filter-checkbox"><input type="checkbox" data-filter-featured /> Featured</label>
        <label class="filter-checkbox"><input type="checkbox" data-filter-trending /> Trending</label>
      </div>
      <button type="button" class="btn btn--secondary btn--sm btn--full" data-filters-clear>Clear filters</button>
    </aside>
    <div>
      <div class="toolbar">
        <span class="toolbar__count" data-result-count>{len(initial_sorted)} {'find' if len(initial_sorted) == 1 else 'finds'}</span>
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
      <div class="grid-products" data-category-grid>{cards if cards else ''}</div>
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
            f'data-gallery-thumb data-full-src="{img}" aria-label="Show image {i+1}"><img src="{img}" alt="" loading="lazy" width="72" height="72" /></button>'
            for i, img in enumerate(images)
        )
        thumbs_html = f'<div class="product-detail__thumbs">{thumbs}</div>'

    highlights = "".join(
        f'<li><svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 10l4 4 8-9"/></svg><span>{esc(h)}</span></li>'
        for h in product.get("highlights", [])
    )
    tags = "".join(f'<span class="tag-pill">{esc(t)}</span>' for t in product.get("tags", []))

    related_cards = "".join(render_product_card(p, reveal=False) for p in related_products)
    related_section = ""
    if related_products:
        related_section = f"""
<section class="section container">
  <div class="section-head"><div><span class="eyebrow">You Might Also Like</span><h2 class="section-title">More from {esc(category['name'])}</h2></div></div>
  <div class="grid-products">{related_cards}</div>
</section>
"""

    body = f"""
<section class="section container" data-product-app data-product-slug="{product['slug']}">
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <a href="/">Home</a><span class="sep">/</span>
    <a href="/category/{category['slug']}/">{esc(category['name'])}</a><span class="sep">/</span>
    <span aria-current="page">{esc(product['name'])}</span>
  </nav>
  <div class="product-detail">
    <div>
      <div class="product-detail__gallery-main"><img src="{product['image']}" alt="{esc(product['name'])}" data-gallery-main loading="eager" /></div>
      {thumbs_html}
    </div>
    <div>
      <span class="product-detail__category">{esc(category_label(product['category']))}{' · ' + esc(product['subcategory']) if product.get('subcategory') else ''}</span>
      <h1 class="product-detail__title">{esc(product['name'])}</h1>
      <div class="product-detail__meta-row">
        <span class="product-detail__price">{format_price(product['price'], product['currency'])}</span>
        {render_stars(product['rating'], product['reviewCount'])}
        {'<span class="badge badge--gold">Trending</span>' if product.get('trending') else ''}
      </div>
      <p class="product-detail__desc">{esc(product['description'])}</p>
      <div class="why-we-like-it">
        <div class="why-we-like-it__label">Why We Like It</div>
        <p>{esc(product['whyWeLikeIt'])}</p>
      </div>
      <ul class="highlights-list">{highlights}</ul>
      <div class="tag-row">{tags}</div>
      <div class="cta-panel">
        <a class="btn btn--primary btn--full" data-affiliate-link data-product-slug="{product['slug']}">View Product {CHEVRON_ICON}</a>
        <p class="cta-panel__disclaimer">You'll leave {esc(site['siteName'])} to view this product on the retailer's site. This may be an affiliate link — see our <a href="/affiliate-disclosure.html" style="color:var(--color-gold-light);">Affiliate Disclosure</a>.</p>
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
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">/</span><span aria-current="page">About</span></nav>
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
      <div class="value-item__desc">We may earn a commission on some links. It never decides what gets featured.</div>
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


def render_affiliate_disclosure_page(site):
    body = f"""
<section class="page-hero container">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">/</span><span aria-current="page">Affiliate Disclosure</span></nav>
  <span class="eyebrow">Legal</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">Affiliate Disclosure</h1>
</section>
<section class="section container narrow">
  <div class="prose">
    <p>PRIME.FINDS is a product discovery publication. Some of the links on this site are affiliate links, which means that if you click through and make a purchase, PRIME.FINDS may earn a commission at no additional cost to you.</p>
    <h2>How this works</h2>
    <p>When you tap "View Product" on a page, you leave PRIME.FINDS and land on the retailer or brand's own website to complete any purchase. We never process payments, store payment details, or handle orders ourselves.</p>
    <h2>How this affects what you see</h2>
    <p>Products are chosen because we think they're genuinely interesting, useful, or well made — not because of the commission they may generate. Whether or not a link is monetized has no bearing on whether a product is featured, and it does not affect the price you pay.</p>
    <h2>Retailer relationships</h2>
    <p>PRIME.FINDS may participate in affiliate programs operated by various retailers and networks. As our retailer relationships are finalized, the specific programs we participate in will be listed here. PRIME.FINDS is an independent publication and is not officially affiliated with, endorsed by, or sponsored by any retailer or brand mentioned on this site unless explicitly stated.</p>
    <h2>Questions</h2>
    <p>If you have questions about a specific link or our affiliate relationships, feel free to reach out through the contact details listed in our footer.</p>
    <p class="text-faint">This page is a general-purpose disclosure and will be updated to reflect the exact requirements of each specific affiliate program PRIME.FINDS joins (for example, Amazon Associates' required program-specific language) before those programs go live.</p>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"Affiliate Disclosure — {site['siteName']}",
        description="How PRIME.FINDS uses affiliate links, and how that does (and doesn't) affect what gets featured.",
        canonical_path="/affiliate-disclosure.html",
        body_html=body,
    )


def render_privacy_page(site):
    body = f"""
<section class="page-hero container">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">/</span><span aria-current="page">Privacy Policy</span></nav>
  <span class="eyebrow">Legal</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">Privacy Policy</h1>
</section>
<section class="section container narrow">
  <div class="prose">
    <p>This placeholder Privacy Policy outlines the general approach PRIME.FINDS takes to visitor data. It should be reviewed and finalized (including any jurisdiction-specific requirements, such as GDPR or CCPA) before the site handles real traffic or collects real user data.</p>
    <h2>Information we collect</h2>
    <ul>
      <li>Basic, aggregated analytics (pages viewed, general location/device type) once an analytics provider is connected — see our analytics abstraction for how this is configured.</li>
      <li>No account is required to browse PRIME.FINDS, and we do not currently collect names, emails, or payment information directly.</li>
    </ul>
    <h2>Cookies</h2>
    <p>PRIME.FINDS does not currently set marketing or tracking cookies of its own. Retailers you're referred to may set their own cookies once you leave our site — their privacy policies govern that data.</p>
    <h2>Third parties</h2>
    <p>Affiliate links direct you to third-party retailers. We are not responsible for the privacy practices of those third-party sites.</p>
    <h2>Changes</h2>
    <p>This policy may be updated as PRIME.FINDS adds new functionality (such as an account system or newsletter). Material changes will be reflected on this page.</p>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"Privacy Policy — {site['siteName']}",
        description="How PRIME.FINDS handles visitor data.",
        canonical_path="/privacy-policy.html",
        body_html=body,
    )


def render_terms_page(site):
    body = f"""
<section class="page-hero container">
  <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">/</span><span aria-current="page">Terms</span></nav>
  <span class="eyebrow">Legal</span>
  <h1 class="section-title" style="font-size: var(--fs-display-lg);">Terms of Use</h1>
</section>
<section class="section container narrow">
  <div class="prose">
    <p>This placeholder outlines general terms for using PRIME.FINDS and should be reviewed by qualified counsel before launch.</p>
    <h2>Nature of the site</h2>
    <p>PRIME.FINDS is a product discovery and editorial publication. Product information (pricing, availability, specifications) is provided for informational purposes and sourced from or verified against the linked retailer at the time of publishing — always confirm current price and availability on the retailer's site before purchasing.</p>
    <h2>No warranty</h2>
    <p>PRIME.FINDS makes no warranties about the products featured, including their quality, safety, or fitness for a particular purpose. Any purchase is a transaction between you and the retailer.</p>
    <h2>Intellectual property</h2>
    <p>Original editorial content, curation, and the PRIME.FINDS brand are the property of PRIME.FINDS. Product images and trademarks belong to their respective owners.</p>
    <h2>Changes to these terms</h2>
    <p>These terms may be updated from time to time; continued use of the site constitutes acceptance of the current version.</p>
  </div>
</section>
"""
    return base_page(
        site,
        title=f"Terms — {site['siteName']}",
        description="Terms of use for PRIME.FINDS.",
        canonical_path="/terms.html",
        body_html=body,
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


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    global _ALL_CATEGORIES
    site, categories, products = load_data()
    _ALL_CATEGORIES = categories

    published = [p for p in products if p.get("published")]
    counts = {}
    for p in published:
        counts[p["category"]] = counts.get(p["category"], 0) + 1

    # ---- Client-side data snapshot (mirrors a future public API response) ----
    write_file(os.path.join(PUBLIC_DIR, "data", "products.json"), json.dumps(published, indent=2))
    write_file(os.path.join(PUBLIC_DIR, "data", "categories.json"), json.dumps(categories, indent=2))

    # ---- Homepage ----
    write_file(os.path.join(PUBLIC_DIR, "index.html"), render_homepage(site, categories, published, counts))

    # ---- Category pages ----
    for category in categories:
        cat_products = [p for p in published if p["category"] == category["slug"]]
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
    write_file(os.path.join(PUBLIC_DIR, "404.html"), render_404_page(site))

    # ---- robots.txt / sitemap.xml / manifest ----
    base_url = site["url"].rstrip("/")
    urls = ["/", "/about.html", "/affiliate-disclosure.html", "/privacy-policy.html", "/terms.html"]
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
