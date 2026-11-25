import { getProducts, getCategories, getCategoryCounts } from '../core/store.js';
import { searchProducts } from '../core/store.js';
import { formatPrice, debounce, escapeHtml } from '../core/utils.js';
import { track, EVENTS } from '../core/analytics.js';
import { lockBackground, restoreFocus } from '../core/dialogs.js';

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
    <p class="search-overlay__hint">או קפצו ישר לקטגוריה</p>
    <div class="search-suggest">${chips}</div>`;
}

export function initSearchOverlay() {
  const overlay = document.querySelector('[data-search-overlay]');
  const openBtns = document.querySelectorAll('[data-search-open]');
  if (!overlay || !openBtns.length) return;

  const input = overlay.querySelector('[data-search-input]');
  const resultsEl = overlay.querySelector('[data-search-results]');
  const closeBtn = overlay.querySelector('[data-search-close]');
  const statusEl = overlay.querySelector('[data-search-status]');

  let productsPromise = null;
  let suggestHtml = null;
  let unlock = null;
  let opener = null;

  // Polite live-region message so screen-reader users hear the outcome of a search.
  const say = (msg) => { if (statusEl) statusEl.textContent = msg; };

  const revealChips = () => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        resultsEl.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-visible'));
      });
    });
  };

  const open = async () => {
    // Never stack on top of another open dialog (the site menu or accessibility options).
    if (overlay.classList.contains('is-open') || document.querySelector('[data-index-panel].is-open, [data-a11y-panel].is-open')) return;
    opener = document.activeElement;
    overlay.classList.add('is-open');
    document.body.classList.add('menu-open');
    unlock = lockBackground(overlay);
    say('');
    productsPromise = productsPromise || getProducts();
    input.value = '';
    // Focus right away (visibility flips instantly), so letters typed straight after
    // opening land in the box instead of being lost while the chips load. Doing it inside
    // the click also lets phones open the keyboard.
    input.focus({ preventScroll: true });
    if (!suggestHtml) {
      const [categories, counts] = await Promise.all([getCategories(), getCategoryCounts()]);
      suggestHtml = categoryChipsMarkup(categories, counts);
    }
    // Only show the category chips if the visitor hasn't started typing meanwhile.
    if (!input.value.trim()) {
      resultsEl.innerHTML = suggestHtml;
      revealChips();
    }
    setTimeout(() => { if (document.activeElement !== input) input.focus({ preventScroll: true }); }, 50);
  };

  const close = ({ restore = true } = {}) => {
    if (!overlay.classList.contains('is-open')) return;
    overlay.classList.remove('is-open');
    document.body.classList.remove('menu-open');
    unlock?.();
    unlock = null;
    say('');
    if (restore) restoreFocus(opener, openBtns[0]);
  };

  const renderResults = async (query) => {
    // The input can fire before open() has run, so start the fetch here too.
    productsPromise = productsPromise || getProducts();
    const [products, categories] = await Promise.all([productsPromise, getCategories()]);
    const catName = Object.fromEntries(categories.map((c) => [c.slug, c.name]));
    if (!query.trim()) {
      resultsEl.innerHTML = suggestHtml || '';
      revealChips();
      say('');
      return;
    }
    const matches = searchProducts(products, query).slice(0, 8);
    track(EVENTS.SEARCH, { query, resultCount: matches.length });

    if (!matches.length) {
      say(`אין תוצאות עבור ${query}.`);
      resultsEl.innerHTML = `
        <div class="state-panel" style="padding: var(--space-lg) 0;">
          <p class="state-panel__title">לא נמצאו מוצרים עבור "${escapeHtml(query)}"</p>
          <p class="text-dim">נסו מילה אחרת, או עיינו לפי קטגוריה.</p>
        </div>`;
      return;
    }

    say(`${matches.length} תוצאות עבור ${query}.`);
    resultsEl.innerHTML = matches
      .map(
        (p, i) => `
        <a class="search-result" href="/product/${p.slug}/" data-reveal style="transition-delay: ${Math.min(i, 5) * 25}ms">
          <img src="${p.thumb || p.image}" alt="" loading="lazy" width="48" height="48" />
          <span>
            <span class="search-result__name">${escapeHtml(p.name)}</span><br/>
            <span class="search-result__meta">${escapeHtml(catName[p.category] || p.category)} · ${formatPrice(p.price, p.currency)}</span>
          </span>
        </a>`
      )
      .join('');
    resultsEl.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => close({ restore: false })));
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
  closeBtn?.addEventListener('click', () => close());
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
