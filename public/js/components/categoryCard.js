import { escapeHtml } from '../core/utils.js';

export function categoryCardMarkup(category, count) {
  return `
    <a class="category-card" href="/category/${category.slug}/" data-reveal>
      <div class="category-card__media">
        <img src="/assets/images/categories/${category.slug}.svg" alt="" loading="lazy" width="1200" height="900" />
      </div>
      <div class="category-card__body">
        <h3 class="category-card__name">${escapeHtml(category.name)}</h3>
        <p class="category-card__desc">${escapeHtml(category.shortDescription)}</p>
        <span class="category-card__count">${count} ${count === 1 ? 'find' : 'finds'}</span>
      </div>
    </a>
  `;
}
