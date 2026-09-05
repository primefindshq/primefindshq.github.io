// ---------------------------------------------------------------------------
// Affiliate link architecture.
//
// This is the ONLY place in the codebase that should decide which URL a
// "View Product" button points to. Nothing else builds or edits an
// affiliate URL — they always come straight from product data (see
// data/products.json / the future Product Hunter + admin dashboard).
//
// When Amazon's (or another network's) official API is connected later,
// only `getProductUrl()` needs to change — every call site stays identical.
// ---------------------------------------------------------------------------

import { track, EVENTS } from './analytics.js';

/**
 * Resolve the URL a "View Product" click should open.
 * Prefers the affiliate URL (monetized) and falls back to the plain
 * external URL if no affiliate URL has been assigned yet — this lets
 * products publish before affiliate attribution is set up, without
 * ever inventing or guessing a URL.
 */
export function getProductUrl(product) {
  return product.affiliateUrl || product.externalUrl || null;
}

/**
 * Attach the correct href + tracking to a "View Product" anchor.
 * Call this once per rendered product CTA rather than hand-writing hrefs.
 */
export function bindAffiliateLink(anchorEl, product, { source = 'unknown' } = {}) {
  const url = getProductUrl(product);
  if (!url) {
    anchorEl.setAttribute('aria-disabled', 'true');
    anchorEl.href = '#';
    anchorEl.addEventListener('click', (e) => e.preventDefault());
    return;
  }

  anchorEl.href = url;
  anchorEl.target = '_blank';
  anchorEl.rel = 'noopener sponsored nofollow';

  anchorEl.addEventListener('click', () => {
    track(EVENTS.AFFILIATE_CLICK, {
      productId: product.id,
      productSlug: product.slug,
      productName: product.name,
      category: product.category,
      source,
    });
    track(EVENTS.EXTERNAL_LINK_CLICK, { url, source });
  });
}

/** Builds the CTA markup used on cards / detail pages so it's never duplicated by hand. */
export function affiliateLinkMarkup(product, { label = 'View Product', className = 'btn btn--primary' } = {}) {
  const disabled = !getProductUrl(product);
  return `<a class="${className}" data-affiliate-link data-product-slug="${product.slug}" ${disabled ? 'aria-disabled="true"' : ''}>
    ${label}
    <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M7 5l6 5-6 5"/></svg>
  </a>`;
}

/** Wires up every `[data-affiliate-link]` inside a container against the given products list. */
export function hydrateAffiliateLinks(container, productsBySlug, source) {
  container.querySelectorAll('[data-affiliate-link]').forEach((el) => {
    const slug = el.getAttribute('data-product-slug');
    const product = productsBySlug.get(slug);
    if (product) bindAffiliateLink(el, product, { source });
  });
}
