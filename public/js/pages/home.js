// Homepage: sections are server-rendered by scripts/build.py for SEO/no-JS
// baseline. This script only hydrates the affiliate CTAs (href + click
// tracking) — affiliate URLs are never written directly into static HTML,
// see js/core/affiliate.js for why.
import { getProducts } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';

document.addEventListener('DOMContentLoaded', async () => {
  const products = await getProducts();
  const bySlug = new Map(products.map((p) => [p.slug, p]));
  hydrateAffiliateLinks(document, bySlug, 'homepage');
});
