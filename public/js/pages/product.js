// Product detail page: gallery thumbnail swapping, affiliate CTA hydration
// (main CTA + related-product cards), and the product_view analytics event.
import { getProducts, getProductBySlug } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';
import { track, EVENTS } from '../core/analytics.js';
import { qs, qsa } from '../core/utils.js';
import { prefersReducedMotion } from '../core/a11y.js';

document.addEventListener('DOMContentLoaded', async () => {
  const app = qs('[data-product-app]');
  if (!app) return;
  const slug = app.dataset.productSlug;

  const products = await getProducts();
  const bySlug = new Map(products.map((p) => [p.slug, p]));
  hydrateAffiliateLinks(document, bySlug, `product:${slug}`);

  const product = await getProductBySlug(slug);
  if (product) {
    track(EVENTS.PRODUCT_VIEW, { productId: product.id, productSlug: product.slug, productName: product.name, category: product.category });
  }

  // Phone-only sticky "View at Amazon" bar: shown while the main CTA panel is
  // off screen, hidden once the real button is in view (CSS limits it to small screens).
  const mobileCta = qs('[data-mobile-cta]', app);
  const ctaPanel = qs('.cta-panel', app);
  if (mobileCta && ctaPanel && 'IntersectionObserver' in window) {
    const setShown = (show) => {
      mobileCta.classList.toggle('is-shown', show);
      mobileCta.setAttribute('aria-hidden', show ? 'false' : 'true');
      mobileCta.querySelector('a')?.setAttribute('tabindex', show ? '0' : '-1');
    };
    new IntersectionObserver(([entry]) => setShown(!entry.isIntersecting), { threshold: 0 }).observe(ctaPanel);
  }

  const mainImg = qs('[data-gallery-main]', app);
  const thumbs = qsa('[data-gallery-thumb]', app);
  thumbs.forEach((thumb) => {
    thumb.addEventListener('click', () => {
      if (thumb.classList.contains('is-active')) return;
      thumbs.forEach((t) => {
        t.classList.remove('is-active');
        t.setAttribute('aria-pressed', 'false');
      });
      thumb.classList.add('is-active');
      thumb.setAttribute('aria-pressed', 'true');
      if (!mainImg) return;
      const nextSrc = thumb.dataset.fullSrc;
      if (prefersReducedMotion()) {
        mainImg.src = nextSrc;
        return;
      }
      // Briefly fade + blur the outgoing image before swapping `src`, so the
      // old and new photo are never both visible in the same frame -- a
      // plain instant swap reads as a jump cut between two products' worth
      // of lighting and framing.
      mainImg.classList.add('is-swapping');
      window.setTimeout(() => {
        mainImg.src = nextSrc;
        mainImg.classList.remove('is-swapping');
      }, 140);
    });
  });
});
