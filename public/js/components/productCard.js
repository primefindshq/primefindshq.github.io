import { formatPrice, renderStars, escapeHtml } from '../core/utils.js';
import { affiliateLinkMarkup } from '../core/affiliate.js';

/**
 * Renders one product card. This is the single template used everywhere a
 * product appears in a grid (trending, latest, category grid, related
 * products, search results) — never hand-duplicated per section.
 */
// Unique ids per rendered card (the server-rendered cards use a "pc" prefix), so the
// link can be named by the product title and described by the blurb, price and rating.
let cardSeq = 0;

const CATEGORY_NAMES = {
  tech: 'Tech', home: 'Home', kitchen: 'Kitchen', gaming: 'Gaming', kids: 'Kids & Baby',
  outdoors: 'Outdoors & Sports', pets: 'Pets', travel: 'Travel', 'desk-setup': 'Desk Setup',
  gifts: 'Gifts', 'under-25': 'Under $25',
};

export function productCardMarkup(product) {
  const cid = `pcj${++cardSeq}`;

  return `
    <article class="product-card" data-reveal>
      <a class="product-card-link" href="/product/${product.slug}/" aria-labelledby="${cid}-name" aria-describedby="${cid}-desc ${cid}-meta">
        <div class="product-card__media">
          <img src="${product.image}" alt="${escapeHtml(product.name)}" loading="lazy" width="800" height="800"
               style="view-transition-name: product-photo-${product.slug}"
               onerror="this.onerror=null;this.src='/assets/images/fallback.svg';" />
        </div>
        <div class="product-card__body">
          <span class="product-card__category">${escapeHtml(CATEGORY_NAMES[product.category] || product.category.replace('-', ' '))}</span>
          <h3 class="product-card__name" id="${cid}-name">${escapeHtml(product.name)}</h3>
          <p class="product-card__desc visually-line-clamp-2" id="${cid}-desc">${escapeHtml(product.shortDescription)}</p>
          <div class="product-card__meta" id="${cid}-meta">
            <span class="product-card__price">${formatPrice(product.price, product.currency)}</span>
            ${renderStars(product.rating, product.reviewCount)}
          </div>
        </div>
      </a>
      <div class="product-card__cta">
        ${affiliateLinkMarkup(product, { label: 'View at Amazon', className: 'btn--ghost btn--icon-trail' })}
      </div>
    </article>
  `;
}

export function productCardSkeleton(count = 8) {
  return Array.from({ length: count }, () => '<div class="product-card__skeleton" aria-hidden="true"></div>').join('');
}
