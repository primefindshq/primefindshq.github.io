// Category page interactivity: search-within-category, filters, sorting, and
// paging (24 cards at a time behind a "Show more" button).
// The initial grid markup is server-rendered (SEO baseline); this script
// re-renders the grid client-side from the full in-memory product list
// whenever the visitor changes a control.
import { getProducts, getProductsByCategory, filterProducts, searchProducts, sortProducts } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';
import { productCardMarkup } from '../components/productCard.js';
import { initCardTilt } from '../components/cardTilt.js';
import { debounce, qs, qsa } from '../core/utils.js';
import { track, EVENTS } from '../core/analytics.js';

document.addEventListener('DOMContentLoaded', async () => {
  const app = qs('[data-category-app]');
  if (!app) return;

  const categorySlug = app.dataset.categorySlug;
  const grid = qs('[data-category-grid]', app);
  const countEl = qs('[data-result-count]', app);
  const sortSelect = qs('[data-sort-select]', app);
  const searchInput = qs('[data-category-search]', app);
  const ratingChips = qsa('[data-filter-rating]', app);
  const subChips = qsa('[data-filter-sub]', app);
  const featuredCheckbox = qs('[data-filter-featured]', app);
  const trendingCheckbox = qs('[data-filter-trending]', app);
  const minPriceInput = qs('[data-filter-min-price]', app);
  const maxPriceInput = qs('[data-filter-max-price]', app);
  const clearBtn = qs('[data-filters-clear]', app);
  const moreWrap = qs('[data-load-more-wrap]', app);
  const moreBtn = qs('[data-load-more]', app);
  const moreStatus = qs('[data-load-more-status]', app);
  const PAGE = 24;
  let currentList = [];
  let shown = PAGE;

  const allProducts = await getProducts();
  const categoryProducts = await getProductsByCategory(categorySlug);
  const bySlug = new Map(allProducts.map((p) => [p.slug, p]));

  track(EVENTS.CATEGORY_VIEW, { category: categorySlug, productCount: categoryProducts.length });

  const state = { sort: 'popular', search: '', subcategory: null, minRating: null, featuredOnly: false, trendingOnly: false, minPrice: null, maxPrice: null };

  // Deep links like /category/gifts/?max=25 (used by the gift guide) pre-set filters.
  const params = new URLSearchParams(location.search);
  const num = (v) => (v !== null && v !== '' && !Number.isNaN(Number(v)) ? Number(v) : null);
  state.maxPrice = num(params.get('max'));
  state.minPrice = num(params.get('min'));
  if (params.get('sort') && sortSelect && [...sortSelect.options].some((o) => o.value === params.get('sort'))) state.sort = params.get('sort');
  if (params.get('q')) state.search = params.get('q');
  if (maxPriceInput && state.maxPrice !== null) maxPriceInput.value = state.maxPrice;
  if (minPriceInput && state.minPrice !== null) minPriceInput.value = state.minPrice;
  if (sortSelect) sortSelect.value = state.sort;
  if (searchInput && state.search) searchInput.value = state.search;

  function updateMore() {
    if (!moreWrap) return;
    const remaining = currentList.length - shown;
    moreWrap.hidden = remaining <= 0;
    if (moreStatus) moreStatus.textContent = `Showing ${Math.min(shown, currentList.length)} of ${currentList.length}`;
    if (moreBtn) moreBtn.textContent = `Show ${Math.min(PAGE, Math.max(remaining, 0))} more`;
  }

  function animateIn(cards) {
    cards.forEach((el, i) => {
      el.style.transitionDelay = `${Math.min(i, 3) * 45}ms`;
      el.addEventListener('transitionend', () => { el.style.transitionDelay = ''; }, { once: true });
    });
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        cards.forEach((el) => el.classList.add('is-visible'));
      });
    });
  }

  function showMore() {
    const next = currentList.slice(shown, shown + PAGE);
    if (!next.length) return;
    const holder = document.createElement('div');
    holder.innerHTML = next.map(productCardMarkup).join('');
    const added = [...holder.children];
    added.forEach((el) => grid.appendChild(el));
    shown += next.length;
    hydrateAffiliateLinks(grid, bySlug, `category:${categorySlug}`);
    initCardTilt(grid);
    animateIn(added.filter((el) => el.matches('[data-reveal]')));
    // Move focus to the first new card so keyboard and screen-reader users land on it.
    added[0]?.querySelector('a')?.focus({ preventScroll: true });
    updateMore();
  }
  moreBtn?.addEventListener('click', showMore);

  function render() {
    let list = categoryProducts;
    if (state.search) list = searchProducts(list, state.search);
    list = filterProducts(list, {
      subcategory: state.subcategory,
      minRating: state.minRating,
      featuredOnly: state.featuredOnly,
      trendingOnly: state.trendingOnly,
      minPrice: state.minPrice,
      maxPrice: state.maxPrice,
    });
    list = sortProducts(list, state.sort);

    countEl.textContent = `${list.length} ${list.length === 1 ? 'find' : 'finds'}`;

    currentList = list;
    shown = PAGE;
    updateMore();

    const html = list.length
      ? list.slice(0, PAGE).map(productCardMarkup).join('')
      : `
        <div class="state-panel" style="grid-column: 1/-1;">
          <svg class="state-panel__icon" viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <p class="state-panel__title">No finds match those filters</p>
          <p>Try widening your price range or clearing a filter.</p>
        </div>`;

    grid.innerHTML = html;
    if (!list.length) return;

    hydrateAffiliateLinks(grid, bySlug, `category:${categorySlug}`);
    initCardTilt(grid);
    // Two rAFs inside animateIn so the opacity:0 starting style is painted
    // before .is-visible is added -- otherwise the fade collapses into one frame.
    animateIn([...grid.querySelectorAll('[data-reveal]')]);
  }

  const debouncedSearch = debounce((value) => {
    state.search = value;
    track(EVENTS.SEARCH, { query: value, scope: `category:${categorySlug}` });
    render();
  }, 200);

  sortSelect?.addEventListener('change', (e) => {
    state.sort = e.target.value;
    track(EVENTS.FILTER_USED, { type: 'sort', value: state.sort, scope: categorySlug });
    render();
  });
  searchInput?.addEventListener('input', (e) => debouncedSearch(e.target.value));
  ratingChips.forEach((chip) =>
    chip.addEventListener('click', () => {
      const value = Number(chip.dataset.filterRating);
      const isActive = chip.classList.contains('is-active');
      ratingChips.forEach((c) => {
        c.classList.remove('is-active');
        c.setAttribute('aria-pressed', 'false');
      });
      if (!isActive) {
        chip.classList.add('is-active');
        chip.setAttribute('aria-pressed', 'true');
        state.minRating = value;
      } else {
        state.minRating = null;
      }
      track(EVENTS.FILTER_USED, { type: 'rating', value: state.minRating, scope: categorySlug });
      render();
    })
  );
  subChips.forEach((chip) =>
    chip.addEventListener('click', () => {
      const isActive = chip.classList.contains('is-active');
      subChips.forEach((c) => {
        c.classList.remove('is-active');
        c.setAttribute('aria-pressed', 'false');
      });
      state.subcategory = null;
      if (!isActive) {
        chip.classList.add('is-active');
        chip.setAttribute('aria-pressed', 'true');
        state.subcategory = chip.dataset.filterSub;
      }
      track(EVENTS.FILTER_USED, { type: 'subcategory', value: state.subcategory, scope: categorySlug });
      render();
    })
  );
  featuredCheckbox?.addEventListener('change', (e) => {
    state.featuredOnly = e.target.checked;
    track(EVENTS.FILTER_USED, { type: 'featured', value: state.featuredOnly, scope: categorySlug });
    render();
  });
  trendingCheckbox?.addEventListener('change', (e) => {
    state.trendingOnly = e.target.checked;
    track(EVENTS.FILTER_USED, { type: 'trending', value: state.trendingOnly, scope: categorySlug });
    render();
  });
  const debouncedPrice = debounce(() => {
    state.minPrice = minPriceInput.value ? Number(minPriceInput.value) : null;
    state.maxPrice = maxPriceInput.value ? Number(maxPriceInput.value) : null;
    track(EVENTS.FILTER_USED, { type: 'price', min: state.minPrice, max: state.maxPrice, scope: categorySlug });
    render();
  }, 300);
  minPriceInput?.addEventListener('input', debouncedPrice);
  maxPriceInput?.addEventListener('input', debouncedPrice);

  clearBtn?.addEventListener('click', () => {
    state.sort = 'popular';
    state.search = '';
    state.subcategory = null;
    state.minRating = null;
    state.featuredOnly = false;
    state.trendingOnly = false;
    state.minPrice = null;
    state.maxPrice = null;
    if (sortSelect) sortSelect.value = 'popular';
    if (searchInput) searchInput.value = '';
    [...ratingChips, ...subChips].forEach((c) => {
      c.classList.remove('is-active');
      c.setAttribute('aria-pressed', 'false');
    });
    if (featuredCheckbox) featuredCheckbox.checked = false;
    if (trendingCheckbox) trendingCheckbox.checked = false;
    if (minPriceInput) minPriceInput.value = '';
    if (maxPriceInput) maxPriceInput.value = '';
    if (location.search) history.replaceState(null, '', location.pathname);
    render();
  });

  // First render replaces the server-rendered "featured" order grid with the
  // exact same data through the same code path used for every interaction —
  // this guarantees the two never drift apart.
  render();
});
