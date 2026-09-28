# PRIME.FINDS — Project Handoff

Last updated: 2026-09-28

## What this project is

PRIME.FINDS is a curated affiliate product-discovery website: a static site that showcases interesting/unusual Amazon products with editorial copy, organized into categories, with "View at Amazon" buttons that carry the owner's Amazon affiliate short links (`https://link.amazon/<code>`). Revenue comes from affiliate commissions, so **the affiliate short link is the only customer-facing link on the site** — regular `amazon.com/...` URLs, ASINs, model numbers, UPCs etc. must never appear in site content, commit messages, or chat output.

- **Live site:** https://primefindshq.github.io (GitHub Pages)
- **Repo:** this directory, pushed to `origin/main`; a push to `main` is what deploys (no CI step — GitHub Pages serves `public/` as committed)
- **Local dev root:** `C:\Users\Admin\Documents\PrimeFinds`

## Architecture

- **Static generator:** `scripts/build.py` (stdlib Python, no dependencies) reads `data/*.json` and renders every HTML page into `public/`. Run it after any data or template change:
  ```
  py scripts/build.py
  ```
- **Preview locally:** `py -m http.server 8950 -d public` then open `http://127.0.0.1:8950/`
- **Data files:**
  - `data/products.json` — the product catalog (source of truth; `public/data/products.json` is a generated mirror, never hand-edited)
  - `data/categories.json` — the 7 categories (tech, home, gaming, travel, desk-setup, gifts, under-25)
  - `data/collections.json` — curated homepage "collections" (added 2026-09-27), each a themed list of product slugs
  - `data/site-config.json` — site name, nav, footer links, contact email, legal dates
- **CSS/JS in `public/`** are hand-written and served as-is (not generated); only HTML is templated by `build.py`.
- **Affiliate link hydration:** affiliate URLs are never written directly into static HTML. Product cards/buttons carry `data-affiliate-link data-product-slug`, and `public/js/core/affiliate.js` fills in the real `href` client-side from `products.json` at runtime. This means a very recent product's affiliate button can briefly appear inert until the browser fetches the JSON (GitHub Pages caches `products.json` ~10 minutes).
- **Design system:** ivory/gold editorial theme, Fraunces + Inter + JetBrains Mono, WebGL entrance animation on the homepage (`js/components/introScene.js`). This is the **reverted-to-baseline** design (commit `c7a5609` + the WebGL entrance only) — an earlier full redesign was tried and explicitly rolled back. **Do not reintroduce that redesign.**
- **Accessibility/legal layer** (shipped 2026-09-20): `public/css/a11y.css`, `public/js/core/a11y.js`, an accessibility statement, cookie notice, rewritten privacy/terms/affiliate-disclosure pages. WCAG 2.2 AA is the target, not a completion claim.

## Standing rules for adding a product (repeat every time)

The user pastes a brief with: product name, the **affiliate short link only** (never the real Amazon URL — don't ask for it), the ASIN to verify against, target categories, and content/positioning guidance (what to say, what NOT to claim). Every time:

1. Open `https://www.amazon.com/dp/<ASIN>` in the browser tool and verify it's the **exact** variant/bundle/color described — not a similar-looking sibling product. If the ASIN's real listing contradicts the brief (wrong model generation, wrong bundle), **stop and ask the user** rather than guessing (this has happened — e.g. SUBSOCCER S3 vs S3 Edge).
2. Pull the product's real hero image straight from Amazon's own CDN (`#landingImage`'s `data-old-hires` attribute) and use it unmodified (`object-fit: contain`, no crop/stretch/edit) — no need to ask the user for an image file unless they want a different (e.g. lifestyle) shot than the default hero.
3. Price stays `null` ("Check price") unless a **current USD price** is reliably verified. To see USD instead of ILS, set the Amazon delivery location to a US zip (e.g. 10001) via the location popover — click "Deliver to Israel" → enter zip → Apply.
4. Only add the `under-25` secondary category when that verified USD price is genuinely below $25 — verify it, don't take the requester's word for it (found real discrepancies doing this: one item the user flagged as Under-25 was actually $84.95; conversely a few unflagged items turned out to qualify).
5. Copy is built **only** from facts stated in the exact listing. Omit health/mood/productivity/superlative/durability claims even if the Amazon listing itself makes them (e.g. a standing-desk-converter listing says "reduce stress and increase productivity" — write the mechanical facts only, drop that framing). If the listing is internally self-contradictory on a spec (has happened with dimensions/weight), state that plainly rather than picking one number to invent certainty.
6. Never touch existing products, their data, their images, their affiliate URLs, or any CSS/JS/animation — additions only.
7. Build (`py scripts/build.py`), sanity-check locally (`py scratchpad-equivalent chk.py`-style diff of old/new product count and confirm `changed existing: []`), commit, push to `main`, then verify the live URL returns 200 and the affiliate button/image are correct (GitHub Pages needs ~30–90s to update after push).
8. **Product-addition requests auto-publish** — no approval needed before going live. This is the one exception to the next rule.

## Standing rule for design/feature work

Anything that isn't "add this product" — redesigns, new site features, UX changes, animation changes — is built and previewed **locally only** and **never committed/pushed** until the user gives explicit go-ahead in chat. (See `deploy-only-after-approval` in Claude's persistent memory.) The 2026-09-27 UX upgrade batch below is the most recent example of this flow.

## Where we left off — current state (as of this file)

**170 products live**, all in `data/products.json` / mirrored to `public/data/products.json`, IDs `prd-0031` through `prd-0200` (gaps below 0031 are pre-existing from before this collaboration started).

### Site features (all live, deployed 2026-09-27, commit `7673d871`)
- **Collections**: a "Hand-picked, by mood" section on the homepage plus 6 standalone `/collection/<slug>/` pages, sourced from `data/collections.json`. Current collections: Desk Glow-Ups, Watch It Move, The Future Home, Kitchen Upgrades That Feel Like Toys, Creator's Corner, Retro & Nostalgic. **These lists have not been updated with any of the ~34 products added after 2026-09-27** — see Next Steps.
- **Smarter search**: token-based (every query word must match somewhere, any order), ranks name/tag hits above description-only hits, normalizes "wi-fi"/"WiFi"/"wi fi", handles a few aliases (polaroid→instax, slushie→slush/slushi, hoover→vacuum). Lives in `public/js/core/store.js`.
- **Category "Type" filter**: subcategory chips with counts on each `/category/<slug>/` page (only shown when a category has ≥2 subcategories with ≥2 products each).
- **"More like this"**: product detail pages now show ranked related products (same subcategory > same category > shared secondary categories > shared tags) instead of just "first 4 in category". Logic is `related_products()` in `scripts/build.py`.
- **Contact email published**: `prime.finds.amazon.10@gmail.com` is now in `data/site-config.json` → appears in the footer, on all legal/accessibility pages' contact section, and the privacy policy was updated to describe what happens if someone emails it. The GitHub issue tracker remains a second, publicly-visible channel.

⚠️ **Known stale memory**: the Claude memory file `ux-upgrade-pending-approval.md` still says this batch is "not deployed" — that's now wrong, it shipped in commit `7673d871`. Worth fixing that memory file, or just noting the git log is the source of truth on this.

### Two large batches of AI-researched products (2026-09-27, after the UX upgrade)

The user asked Claude to research and shortlist products the site didn't have yet, present them with rationale, and the user then supplied only the affiliate short links (no ASINs) in numbered order matching the shortlist, skipping some numbers. Claude used its own research ASINs to find/verify each real listing.

- **Batch 1** — 18 products, commit `6d4738be`: MOVA Self Rotating Globe, MOOCCI Levitating Bulb Lamp, Wood Trick Cyber Hand puzzle, Eilik DQ robot, RayCue Maclock retro pixel clock, ATuMan Mooda thermometer, LaMetric TIME, Marshall Emberton III speaker, 8BitDo Retro Cube 2 speaker, Crosley Rondo speaker, WSTER Cyberpunk Truck speaker, Stylophone, Otamatone, Heated Ice Cream Scoop, Genuine Fred Pizza Boss 3000, Al Dente singing pasta timer, LuvLink Friendship Lamp, Victrola Willow radio.
- **Batch 2** — 16 products, commit `bc943389`: Rubik's Connected smart cube, OLEOCA tabletop pinball, Crosley Cruiser Plus turntable, FiayaCom Bluetooth retro rotary phone, AeroGarden Bounty, Click & Grow Smart Garden 3, OutIn Nano portable espresso, BigBlue foldable solar charger, rechargeable hand warmers (2-pack), ULANZI VL119 RGB light wand, TOMLOV P50 digital microscope, PhoneSoap 3 UV sanitizer, Rocketbook Core reusable notebook, VIVO standing desk converter, MOUNTRAX cordless neck/shoulder massager, PlayShifu Orboot Earth AR globe.

Every one of these 34 was verified against its real Amazon listing (title, price in USD via zip 10001, image, specs) exactly per the standing rules above before publishing — nothing was invented from the research shortlist blind.

### Most recent conversation thread (not code-related)

The user had a cross-device sync confusion (opened Claude on a second computer, it showed "Can't reach your computer" / stale history) — resolved by enabling Remote Control for this session (`mcp__ccd_session_mgmt__set_remote_control`). Then the user asked for a TikTok/Instagram "10 Amazon Finds"-style video — Claude picked 10 high visual-impact products from the 34 new ones (MOOCCI Levitating Bulb, MOVA Globe, LuvLink Friendship Lamp, WSTER Cyberpunk Truck Speaker, Al Dente singing pasta timer, Genuine Fred Pizza Boss 3000, Heated Ice Cream Scoop, FiayaCom retro rotary phone, RayCue Maclock clock, PlayShifu Orboot Earth) based on general knowledge of the format, since the two video files the user shared couldn't actually be viewed (Read tool file-size-rejected the WhatsApp HTML export; the MP4 file:// navigation attempt was rejected by the user mid-tool-call). **This is unresolved** — if video-style guidance is still wanted, the user needs to describe the reference video's pacing/tone/music in words, or find another way to share it that Claude's tools can actually open.

## Decisions worth knowing about

- **72 older products** (pre-dating this collaboration) still have the real `amazon.com/dp/...?tag=...` URL sitting in their `externalUrl` field in `products.json` (their `affiliateUrl` field, which is what the site actually uses, is fine — short `amzn.to` links). The user was asked whether to clean this up and explicitly said to leave it: "if it's not visible and doesn't matter, I don't care — it's just links." Do not spend time on this unless asked again.
- The site's `Under $25` category assignment has caught real mistakes when just trusting the requester's guess vs. actually checking USD price — always verify.
- One SKU (SUBSOCCER, `prd-0166`) is intentionally named "S3 Edge" rather than the plain "S3" the user originally asked for, because the supplied ASIN's real Amazon listing turned out to be the newer S3 Edge — flagged to the user, who confirmed publishing it under the accurate name.

## Suggested next steps

1. **Add the 34 newest products into `data/collections.json`** where they fit thematically (e.g. MOVA Globe / MOOCCI Levitating Lamp → "Watch It Move" or "Desk Glow-Ups"; Crosley Cruiser Plus / Victrola Willow / FiayaCom rotary phone → "Retro & Nostalgic"; AeroGarden / Click & Grow / OutIn Nano → possibly a new "future kitchen" style collection; ULANZI wand / TOMLOV microscope → "Creator's Corner"). Right now the collections only reflect the catalog as it stood before 2026-09-27's research batches.
2. **Fix the stale `ux-upgrade-pending-approval` memory file** (it says "not deployed"; it has been deployed since commit `7673d871`).
3. If the user wants another round of AI-researched product suggestions, the working pattern is: Claude searches Amazon directly (browser tool, checking against the existing catalog to avoid duplicates), presents ~20 candidates with ASIN + rationale + rough USD price, the user replies with only affiliate short links in the same numbered order (skipping any they don't want), and Claude re-verifies each one fully before publishing.
4. Resolve the still-open TikTok/Reels video request if the user brings it back — get a description or a link Claude's browser tool can actually open, rather than a file it can't render.
5. General site-quality backlog the user has heard and not yet acted on (not blocking, just noted from an earlier "what should we upgrade" conversation): possibly swap a few product hero images where a marketing/lifestyle shot was used instead of Amazon's plain product-only hero; consider inlining affiliate hrefs into the static HTML at build time (with client JS as a fallback) to avoid the ~10-minute GitHub Pages cache window where a brand-new product's button can look inert.
