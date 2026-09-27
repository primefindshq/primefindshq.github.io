// Collection pages: the grid is server-rendered by scripts/build.py; this script only
// hydrates the affiliate CTAs, exactly like the homepage (see js/core/affiliate.js).
import { getProducts } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';

document.addEventListener('DOMContentLoaded', async () => {
  const products = await getProducts();
  const bySlug = new Map(products.map((p) => [p.slug, p]));
  hydrateAffiliateLinks(document, bySlug, 'collection');
});
