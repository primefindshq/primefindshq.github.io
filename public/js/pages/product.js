// Product detail page: gallery thumbnail swapping, affiliate CTA hydration
// (main CTA + related-product cards), and the product_view analytics event.
import { getProducts, getProductBySlug } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';
import { track, EVENTS } from '../core/analytics.js';
import { qs, qsa } from '../core/utils.js';

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

  const mainImg = qs('[data-gallery-main]', app);
  const thumbs = qsa('[data-gallery-thumb]', app);
  thumbs.forEach((thumb) => {
    thumb.addEventListener('click', () => {
      thumbs.forEach((t) => t.classList.remove('is-active'));
      thumb.classList.add('is-active');
      if (mainImg) mainImg.src = thumb.dataset.fullSrc;
    });
  });
});
