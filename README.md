# PRIME.FINDS

A premium, international product-discovery brand: curated products, smart finds, no endless searching. This repo is the full production website — homepage, category pages, product detail pages, search, filtering, legal pages — built on a data architecture designed to plug into a future automated "Product Hunter" and an admin dashboard without a rewrite.

## 1. Summary of what was built

- **Full site**: homepage (hero, Trending Now, Categories, Latest Finds, Featured Product), 7 category pages, 29 product detail pages, About, Affiliate Disclosure, Privacy Policy, Terms, 404.
- **Design system**: black/near-black background, metallic gold accent, warm white type, Fraunces (display serif) + Inter (body sans), CSS custom-property tokens for color/type/spacing/radius/shadow/motion.
- **Product data model**: a single JSON "database" (`data/products.json`) with every field requested (id, slug, category, pricing, rating, tags, affiliate/external URLs, featured/trending/published flags, timestamps, etc.), plus `data/categories.json` and `data/site-config.json`.
- **Static site generator** (`scripts/build.py`): renders every page from that data — this is what makes "hundreds or thousands of products" a data problem, not a code problem. Add a product to the JSON, rebuild, get a fully SEO-tagged page.
- **Search, filter, sort**: client-side, working today, built to scale.
- **Affiliate link architecture**: one function (`getProductUrl`) and one hydration path — never hand-written hrefs.
- **Analytics abstraction**: a `track()` call site the whole app shares; no vendor is wired in yet, and none is required for the site to work.
- **Placeholder demo content**: 29 original (non-copied) demo products across all 7 categories, plus generated abstract gold/black SVG art standing in for product photography.
- **Placeholder logo**: a gold "P/F" monogram + wordmark matching the brand's described visual identity, wired into header/footer/mobile nav/favicon — see [Logo](#7-logo--important) below.

## 2. Important deviation from the original tech-stack request — please read

The brief asked for **Next.js + TypeScript**. This machine has **no Node.js/npm installed** (confirmed — not present anywhere, no nvm, no portable install), so a Next.js app could not actually be run, built, or tested here, which the brief also explicitly required ("run the application," "production build succeeds"). You chose, when asked, to proceed with a **statically-generated HTML/CSS/vanilla-JS site** built with Python (stdlib only, no dependencies) standing in for the Next.js build step.

Concretely:

| Next.js concept | What this project uses instead |
|---|---|
| `generateStaticParams` + page components | `scripts/build.py` — reads the JSON data and renders one HTML file per product/category |
| `generateMetadata` (per-page SEO) | Same `build.py`, computed per product/category into `<title>`, meta description, canonical, OG/Twitter tags, JSON-LD |
| React components | Plain-function HTML renderers in Python (`render_product_card`, etc.) and mirrored JS renderers (`productCard.js`) for client-side re-rendering (filters/sort/search) |
| API routes / server data fetching | Static JSON snapshot at `public/data/*.json`, fetched client-side |
| TypeScript types | Documented field lists in this README + consistent object shapes in the JSON data (see §4) |

**This was a deliberate, scoped substitution, not a shortcut** — the architecture (one JSON source of truth → generated pages → thin client hydration for interactivity) maps almost 1:1 onto Next.js if/when Node is available: each `render_*` function in `build.py` becomes a page/layout component, `data/products.json` becomes your database seed. Section 8 below covers the migration path.

## 3. Project structure

```
PrimeFinds/
├── data/                        # THE SOURCE OF TRUTH ("database")
│   ├── products.json            # every product — this is what a future
│   │                            #   admin dashboard / Product Hunter writes to
│   ├── categories.json          # the 7 categories (add more anytime)
│   └── site-config.json         # nav links, footer links, social URLs, tagline
├── scripts/
│   ├── build.py                 # static site generator — run after editing data/
│   └── generate_art.py          # generates placeholder SVG product/category art
├── public/                      # THE DEPLOYABLE SITE (generated + static assets)
│   ├── index.html               # ← generated
│   ├── about.html, terms.html, privacy-policy.html,
│   │   affiliate-disclosure.html, 404.html   # ← generated
│   ├── category/<slug>/index.html            # ← generated, one per category
│   ├── product/<slug>/index.html             # ← generated, one per PUBLISHED product
│   ├── data/products.json, categories.json    # ← generated client-side data snapshot
│   ├── sitemap.xml, robots.txt, site.webmanifest  # ← generated
│   ├── css/                     # tokens.css, base.css, layout.css,
│   │                            #   components.css, animations.css, pages.css
│   ├── js/
│   │   ├── core/                # store.js (data queries), affiliate.js,
│   │   │                        #   analytics.js, utils.js
│   │   ├── components/          # productCard.js, categoryCard.js, nav.js,
│   │   │                        #   searchOverlay.js, reveal.js
│   │   ├── pages/                # home.js, category.js, product.js
│   │   └── main.js              # shared init (header, search, scroll-reveal)
│   └── assets/
│       ├── logo/                # mark.svg, wordmark.svg, favicon.svg (placeholders — see §7)
│       └── images/              # generated placeholder art (products/categories/hero)
├── .env.example
└── README.md
```

**Rule of thumb:** edit files in `data/` and `scripts/`; everything in `public/*.html` and `public/data/*.json` is *generated* — re-running `build.py` overwrites it.

## 4. Product data model

Every product in `data/products.json` has this shape (matches the brief exactly, plus `highlights`):

```jsonc
{
  "id": "prd-0001",
  "name": "Aurora Mini Projector",
  "slug": "aurora-mini-projector",
  "category": "tech",                 // must match a categories.json slug
  "subcategory": "Home Entertainment",
  "description": "...",               // long, product detail page
  "shortDescription": "...",          // card blurb + meta description
  "whyWeLikeIt": "...",
  "highlights": ["...", "..."],       // bullet list on detail page
  "image": "/assets/images/products/aurora-mini-projector.svg",
  "additionalImages": ["...", "..."],
  "price": 179.0,
  "currency": "USD",
  "rating": 4.7,
  "reviewCount": 812,
  "tags": ["projector", "home cinema", "portable"],
  "affiliateUrl": "https://affiliate.invalid/...",   // see §6
  "externalUrl": "https://retailer.invalid/...",
  "featured": true,
  "trending": true,
  "published": true,                  // false = hidden everywhere (moderation gate)
  "createdAt": "2026-08-29T10:00:00.000Z",
  "updatedAt": "2026-08-29T10:00:00.000Z"
}
```

`published: false` is already wired end-to-end as the future admin "approve/reject" gate: `build.py` never generates a page for an unpublished product, and never includes it in `public/data/products.json` — so it can't appear in search, category grids, or related products either. One demo product (`prowave-noise-cancelling-headphones`) is deliberately left unpublished to prove this out.

## 5. How to run the project

**1. Regenerate placeholder art** (only needed if you edit `data/products.json` / `data/categories.json` and want new SVG art for new slugs):

```bash
python scripts/generate_art.py
```

**2. Build the site** (run this after any change to files in `data/`):

```bash
python scripts/build.py
```

**3. Serve it locally:**

```bash
cd public
python -m http.server 8420
```

Then open `http://localhost:8420/`. (On this machine, `python` may need to be `py` — e.g. `py scripts/build.py`.)

There is no npm install, no build tool, no bundler — the whole toolchain is the Python standard library.

## 6. Affiliate link architecture

`public/js/core/affiliate.js` is the **only** place in the codebase that resolves a "View Product" URL:

```js
getProductUrl(product) // → product.affiliateUrl || product.externalUrl || null
```

Every CTA (product cards, product detail page, related products) renders as an inert `<a data-affiliate-link data-product-slug="...">` — the real `href`, `target`, `rel`, and click-tracking are attached client-side by `hydrateAffiliateLinks()` reading straight from `data/products.json`. Nothing hand-writes a URL into HTML. When Amazon's (or another network's) API is connected, only `getProductUrl()` changes.

**All demo affiliate/external URLs point to the reserved `.invalid` TLD** (e.g. `https://affiliate.invalid/prime-finds-demo/...`) — guaranteed not to resolve, so they can never be mistaken for a real, clickable affiliate link during development. Swap in real URLs per-product in `data/products.json` when real affiliate relationships exist.

## 7. Logo — important

The image you shared in chat (the gold "P/F" monogram wordmark) could not be extracted as a file — this session only has filesystem access, not the ability to save an image pasted into chat. **The three logo files at `public/assets/logo/` are placeholders I built to match that visual identity** (gold gradient monogram + wordmark), not the exact supplied asset.

**To use your real logo:** replace these three files, keeping the exact filenames:
- `public/assets/logo/mark.svg` (compact monogram)
- `public/assets/logo/wordmark.svg` (full lockup — used in header/footer)
- `public/assets/logo/favicon.svg` (browser tab icon)

Every page references these paths, so dropping in the real files updates the whole site instantly — no code changes needed. (See `public/assets/logo/README.md`.)

## 8. What remains to be configured

- **Real logo files** (§7).
- **Real domain**: `data/site-config.json` → `"url"` is currently `https://primefinds.example`; canonical URLs, OG tags, and the sitemap all derive from it.
- **Instagram URL**: `data/site-config.json` → `"social.instagram"` is intentionally blank (footer shows a disabled icon until it's filled in) — no URL was invented.
- **Analytics provider**: set `window.__PRIME_FINDS_ANALYTICS_CONFIG` (see `public/js/core/analytics.js`) once GA4/Plausible/etc. is chosen. Nothing needs to change elsewhere.
- **Real affiliate URLs** once retailer/network relationships exist (§6).
- **Real product photography** — drop files into `public/assets/images/products/` and update the `image`/`additionalImages` paths in `data/products.json`.
- **Affiliate Disclosure page** should get the specific required language of whichever affiliate program(s) you join (e.g. Amazon Associates' mandated wording) — currently a general, honest, program-agnostic disclosure.
- **Legal pages** (Privacy/Terms) are reasonable starting drafts, not legal advice — have them reviewed before real traffic/data collection.

## 9. Known limitations

- No Node/Next.js/React — see §2 for why and the migration path in §10.
- No build-time image optimization (no Next.js `<Image>` equivalent) — the demo art is hand-generated SVG (tiny, vector, no optimization needed); real product photos should be pre-sized/compressed before adding.
- No true multi-size favicon set (ICO/PNG for older browsers/platforms) — only a modern SVG favicon. Generate a full favicon set from the final logo before launch.
- Category/product filtering and sorting are entirely client-side against the full product list for that scope — fine at hundreds of products, but a true "thousands of products" catalog should paginate via a real API instead of shipping the whole JSON to the client.
- No automated test suite — verification was manual (build run, local server, in-browser check across desktop/mobile viewports, link/status checks).

## 10. Product Hunter & admin dashboard integration (future — not built yet)

**Where products live today:** `data/products.json`, one flat array, one object per product, shape documented in §4.

**How the future automation should connect:**

1. **Product Hunter writes candidates**, not live products. Give it its own file/table (e.g. `data/product-candidates.json` or a real DB table `product_candidates`) with the *same field shape* as `data/products.json` plus a status field (`pending_review` / `approved` / `rejected`) and whatever scoring/source metadata it wants to attach. **Never** have it write directly into `data/products.json` — that file (or its DB successor) should only ever contain admin-approved products.
2. **Admin dashboard (`/admin`, not built yet)** reads `product-candidates`, lets you edit fields, assign category, set the affiliate URL, and Approve/Reject. Approve = copy the record (with `published: true`) into `data/products.json` (or the products table); Reject = mark it rejected and leave it out.
3. **Rebuild**: once products.json/the DB changes, re-run `scripts/build.py` (or, post-Next.js-migration, redeploy/revalidate) to regenerate pages. If this moves to a real database, `build.py`'s `load_data()` function is the only place that needs to change — query the DB instead of reading JSON, and every `render_*` function downstream keeps working unmodified.
4. **The `published` flag already does the "is this live" gating** end-to-end (see §4) — the admin dashboard's Approve action is really just flipping that flag (plus setting `featured`/`trending` as desired) and re-running the build.

## 11. Migrating to Next.js later

When Node.js is available:
- `data/*.json` → seed data for a real DB, or keep as-is and read at build time.
- Each `render_*` function in `scripts/build.py` → a React Server Component / page (`app/product/[slug]/page.tsx`, `app/category/[slug]/page.tsx`, etc.), using `generateStaticParams` over the same product/category lists.
- Each `render_*`'s inline HTML string → JSX with the same class names (the CSS in `public/css/*.css` can move over almost unchanged as global stylesheets, or be ported to CSS Modules/Tailwind).
- `public/js/core/store.js`, `affiliate.js`, `analytics.js` → port near-verbatim as TypeScript modules; the function signatures were written to be framework-agnostic on purpose.
- `public/js/pages/category.js`'s filter/sort/search logic → a client component (`"use client"`) using the same state shape.
