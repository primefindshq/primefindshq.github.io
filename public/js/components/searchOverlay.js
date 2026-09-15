import { getProducts, getCategories, getCategoryCounts } from '../core/store.js';
import { searchProducts } from '../core/store.js';
import { formatPrice, debounce, escapeHtml } from '../core/utils.js';
import { track, EVENTS } from '../core/analytics.js';

function categoryChipsMarkup(categories, counts) {
  const chips = categories
    .map(
      (c, i) => `
      <a class="search-suggest__chip" href="/category/${c.slug}/" data-reveal style="transition-delay: ${Math.min(i, 6) * 30}ms">
        <span>${escapeHtml(c.name)}</span>
        <span class="search-suggest__chip-count">${counts[c.slug] || 0}</span>
      </a>`
    )
    .join('');
  return `
    <p class="search-overlay__hint">Or jump straight into a category</p>
    <div class="search-suggest">${chips}</div>`;
}

export function initSearchOverlay() {
  const overlay = document.querySelector('[data-search-overlay]');
  const openBtns = document.querySelectorAll('[data-search-open]');
  if (!overlay || !openBtns.length) return;

  const input = overlay.querySelector('[data-search-input]');
  const resultsEl = overlay.querySelector('[data-search-results]');
  const closeBtn = overlay.querySelector('[data-search-close]');

  let productsPromise = null;
  let suggestHtml = null;

  const revealChips = () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        resultsEl.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-visible'));
      });
    });
  };

  const open = async () => {
    overlay.classList.add('is-open');
    document.body.classList.add('menu-open');
    productsPromise = productsPromise || getProducts();
    input.value = '';
    if (!suggestHtml) {
      const [categories, counts] = await Promise.all([getCategories(), getCategoryCounts()]);
      suggestHtml = categoryChipsMarkup(categories, counts);
    }
    resultsEl.innerHTML = suggestHtml;
    revealChips();
    setTimeout(() => input.focus(), 50);
  };

  const close = () => {
    overlay.classList.remove('is-open');
    document.body.classList.remove('menu-open');
  };

  const renderResults = async (query) => {
    const products = await productsPromise;
    if (!query.trim()) {
      resultsEl.innerHTML = suggestHtml || '';
      revealChips();
      return;
    }
    const matches = searchProducts(products, query).slice(0, 8);
    track(EVENTS.SEARCH, { query, resultCount: matches.length });

    if (!matches.length) {
      resultsEl.innerHTML = `
        <div class="state-panel" style="padding: var(--space-lg) 0;">
          <p class="state-panel__title">No finds match "${escapeHtml(query)}"</p>
          <p class="text-dim">Try a different word, or browse by category instead.</p>
        </div>`;
      return;
    }

    resultsEl.innerHTML = matches
      .map(
        (p, i) => `
        <a class="search-result" href="/product/${p.slug}/" data-reveal style="transition-delay: ${Math.min(i, 5) * 25}ms">
          <img src="${p.image}" alt="" loading="lazy" width="48" height="48" />
          <span>
            <span class="search-result__name">${escapeHtml(p.name)}</span><br/>
            <span class="search-result__meta">${escapeHtml(p.category)} · ${formatPrice(p.price, p.currency)}</span>
          </span>
        </a>`
      )
      .join('');
    // Two rAFs so the browser paints the opacity:0 starting style before
    // .is-visible flips it -- see category.js for why one isn't enough.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        resultsEl.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-visible'));
      });
    });
  };

  const debouncedRender = debounce((q) => renderResults(q), 180);

  openBtns.forEach((btn) => btn.addEventListener('click', open));
  closeBtn?.addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      overlay.classList.contains('is-open') ? close() : open();
    }
  });
  input?.addEventListener('input', (e) => debouncedRender(e.target.value));
}
