// Category page interactivity: search-within-category, filters, sorting.
// The initial grid markup is server-rendered (SEO baseline); this script
// re-renders the grid client-side from the full in-memory product list
// whenever the visitor changes a control.
import { getProducts, filterProducts, searchProducts, sortProducts } from '../core/store.js';
import { hydrateAffiliateLinks } from '../core/affiliate.js';
import { productCardMarkup } from '../components/productCard.js';
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
  const featuredCheckbox = qs('[data-filter-featured]', app);
  const trendingCheckbox = qs('[data-filter-trending]', app);
  const minPriceInput = qs('[data-filter-min-price]', app);
  const maxPriceInput = qs('[data-filter-max-price]', app);
  const clearBtn = qs('[data-filters-clear]', app);

  const allProducts = await getProducts();
  const categoryProducts = allProducts.filter((p) => p.category === categorySlug);
  const bySlug = new Map(allProducts.map((p) => [p.slug, p]));

  track(EVENTS.CATEGORY_VIEW, { category: categorySlug, productCount: categoryProducts.length });

  const state = { sort: 'featured', search: '', minRating: null, featuredOnly: false, trendingOnly: false, minPrice: null, maxPrice: null };

  function render() {
    let list = categoryProducts;
    if (state.search) list = searchProducts(list, state.search);
    list = filterProducts(list, {
      minRating: state.minRating,
      featuredOnly: state.featuredOnly,
      trendingOnly: state.trendingOnly,
      minPrice: state.minPrice,
      maxPrice: state.maxPrice,
    });
    list = sortProducts(list, state.sort);

    countEl.textContent = `${list.length} ${list.length === 1 ? 'find' : 'finds'}`;

    if (!list.length) {
      grid.innerHTML = `
        <div class="state-panel" style="grid-column: 1/-1;">
          <svg class="state-panel__icon" viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <p class="state-panel__title">No finds match those filters</p>
          <p>Try widening your price range or clearing a filter.</p>
        </div>`;
      return;
    }

    grid.innerHTML = list.map(productCardMarkup).join('');
    hydrateAffiliateLinks(grid, bySlug, `category:${categorySlug}`);
    grid.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-visible'));
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
      ratingChips.forEach((c) => c.classList.remove('is-active'));
      if (!isActive) {
        chip.classList.add('is-active');
        state.minRating = value;
      } else {
        state.minRating = null;
      }
      track(EVENTS.FILTER_USED, { type: 'rating', value: state.minRating, scope: categorySlug });
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
    state.sort = 'featured';
    state.search = '';
    state.minRating = null;
    state.featuredOnly = false;
    state.trendingOnly = false;
    state.minPrice = null;
    state.maxPrice = null;
    if (sortSelect) sortSelect.value = 'featured';
    if (searchInput) searchInput.value = '';
    ratingChips.forEach((c) => c.classList.remove('is-active'));
    if (featuredCheckbox) featuredCheckbox.checked = false;
    if (trendingCheckbox) trendingCheckbox.checked = false;
    if (minPriceInput) minPriceInput.value = '';
    if (maxPriceInput) maxPriceInput.value = '';
    render();
  });

  // First render replaces the server-rendered "featured" order grid with the
  // exact same data through the same code path used for every interaction —
  // this guarantees the two never drift apart.
  render();
});
