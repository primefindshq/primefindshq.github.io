// Video landing pages (/v/): the grid is server-rendered by scripts/build.py; this script
// hydrates the affiliate CTAs (like collections) and makes the number bar jump reliably,
// even while lazy images above the target are still loading and shifting the layout.
import { getProducts } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';

function jumpTo(id, smooth) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: smooth ? 'smooth' : 'instant', block: 'start' });
  // Re-align once nearby images have settled.
  window.setTimeout(() => el.scrollIntoView({ behavior: 'instant', block: 'start' }), 700);
}

document.addEventListener('DOMContentLoaded', async () => {
  document.querySelectorAll('.video-jump__num').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const id = a.getAttribute('href').slice(1);
      history.replaceState(null, '', `#${id}`);
      jumpTo(id, true);
    });
  });
  if (location.hash.length > 1) jumpTo(location.hash.slice(1), false);

  const products = await getProducts();
  const bySlug = new Map(products.map((p) => [p.slug, p]));
  hydrateAffiliateLinks(document, bySlug, 'video');
});
