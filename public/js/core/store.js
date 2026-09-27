// ---------------------------------------------------------------------------
// Product data store — the single client-side entry point to product data.
//
// Today this fetches static JSON snapshots generated at build time from
// data/products.json + data/categories.json (see scripts/build.py). When the
// automated Product Hunter + admin dashboard exist, this file is the ONLY
// thing that needs to change: swap `fetchProducts()` to call a real API
// (e.g. `/api/products`) and every page that imports from here keeps working
// unmodified, because they only ever go through the query helpers below.
// ---------------------------------------------------------------------------

let productsCache = null;
let categoriesCache = null;

async function fetchJson(path) {
  const res = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}

export async function getProducts() {
  if (!productsCache) {
    const all = await fetchJson('/data/products.json');
    // Only published products are ever exposed to the live site — this is
    // the same gate an admin "approve/reject" workflow would sit in front of.
    productsCache = all.filter((p) => p.published);
  }
  return productsCache;
}

export async function getCategories() {
  if (!categoriesCache) {
    categoriesCache = (await fetchJson('/data/categories.json')).sort((a, b) => a.order - b.order);
  }
  return categoriesCache;
}

export async function getProductBySlug(slug) {
  const products = await getProducts();
  return products.find((p) => p.slug === slug) || null;
}

export async function getCategoryBySlug(slug) {
  const categories = await getCategories();
  return categories.find((c) => c.slug === slug) || null;
}

/** A product belongs to its primary category plus any listed secondaryCategories --
 * lets one product (e.g. a candle warmer that's both home decor and a gift) surface
 * in more than one category grid without duplicating the product entry. */
function isInCategory(product, categorySlug) {
  return product.category === categorySlug || (product.secondaryCategories || []).includes(categorySlug);
}

export async function getProductsByCategory(categorySlug) {
  const products = await getProducts();
  return products.filter((p) => isInCategory(p, categorySlug));
}

export async function getCategoryCounts() {
  const products = await getProducts();
  const counts = {};
  for (const p of products) {
    for (const slug of [p.category, ...(p.secondaryCategories || [])]) counts[slug] = (counts[slug] || 0) + 1;
  }
  return counts;
}

export async function getRelatedProducts(product, limit = 4) {
  const products = await getProducts();
  return products
    .filter((p) => p.slug !== product.slug && p.category === product.category)
    .slice(0, limit);
}

export async function getFeaturedProduct() {
  const products = await getProducts();
  return products.find((p) => p.featured) || products[0] || null;
}

export async function getTrendingProducts(limit = 8) {
  const products = await getProducts();
  return products.filter((p) => p.trending).slice(0, limit);
}

export async function getLatestProducts(limit = 8) {
  const products = await getProducts();
  return [...products]
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, limit);
}

/** Sort a product list. Supports the sort keys used across category pages / "Latest Finds". */
export function sortProducts(products, sortKey) {
  const list = [...products];
  switch (sortKey) {
    case 'newest':
      return list.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    case 'price-asc':
      // unknown price ("Check price") always sorts last, regardless of direction
      return list.sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity));
    case 'price-desc':
      return list.sort((a, b) => (b.price ?? -Infinity) - (a.price ?? -Infinity));
    case 'rating':
      return list.sort((a, b) => b.rating - a.rating);
    case 'trending':
      return list.sort((a, b) => Number(b.trending) - Number(a.trending));
    case 'featured':
      return list.sort((a, b) => Number(b.featured) - Number(a.featured));
    default:
      return list;
  }
}

// Search normalisation: lowercase, drop accents and punctuation ("Wi-Fi" -> "wi fi",
// "Nanoleaf's" -> "nanoleaf s"), collapse whitespace, so "wifi lamp", "wi-fi lamp"
// and "Lamp, WiFi" behave alike.
function normalise(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/wi-?\s?fi/g, 'wifi')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

// A few everyday words people type that the product copy phrases differently.
const SEARCH_ALIASES = {
  polaroid: ['instax'],
  slushie: ['slush', 'slushi'],
  slushy: ['slush', 'slushi'],
  hoover: ['vacuum'],
};


function fieldScore(field, token) {
  if (!field) return 0;
  if (field.split(' ').some((w) => w === token)) return 2; // whole-word hit
  // partial hit (prefix / inside a word) -- but very short words must match whole, or "tv" finds every "activity"
  return token.length >= 3 && field.includes(token) ? 1 : 0;
}

/** Client-side search across name / category / tags / description.
 *  Every word of the query must be found somewhere in the product (in any order);
 *  results are ranked so name and tag matches come before description-only matches. */
export function searchProducts(products, query) {
  const tokens = normalise(query).split(' ').filter(Boolean);
  if (!tokens.length) return [];
  const scored = [];
  for (const p of products) {
    const name = normalise(p.name);
    const tags = normalise((p.tags || []).join(' '));
    const meta = normalise([p.category, p.subcategory, ...(p.secondaryCategories || [])].join(' '));
    const body = normalise([p.shortDescription, p.description].join(' '));
    let total = 0;
    let ok = true;
    for (const token of tokens) {
      const options = [token, ...(SEARCH_ALIASES[token] || [])];
      let best = 0;
      options.forEach((opt, idx) => {
        const weight = idx === 0 ? 1 : 0.6; // an alias counts a bit less than the exact word
        const s =
          fieldScore(name, opt) * 6 + fieldScore(tags, opt) * 4 + fieldScore(meta, opt) * 3 + fieldScore(body, opt) * 1;
        best = Math.max(best, s * weight);
      });
      if (best === 0) { ok = false; break; }
      total += best;
    }
    if (ok) scored.push({ p, total });
  }
  // stable: equal scores keep catalogue order
  return scored.map((x, i) => ({ ...x, i })).sort((a, b) => b.total - a.total || a.i - b.i).map((x) => x.p);
}

/** Apply the shared filter set used on category pages. */
export function filterProducts(products, filters) {
  return products.filter((p) => {
    if (filters.categories?.length && !filters.categories.some((c) => isInCategory(p, c))) return false;
    // a product with no confirmed price can't be verified against a price filter, so it's excluded
    // rather than guessed at when one is active (it still shows normally with no filter applied).
    if (filters.minPrice != null && (p.price == null || p.price < filters.minPrice)) return false;
    if (filters.maxPrice != null && (p.price == null || p.price > filters.maxPrice)) return false;
    if (filters.subcategory && p.subcategory !== filters.subcategory) return false;
    if (filters.minRating != null && p.rating < filters.minRating) return false;
    if (filters.featuredOnly && !p.featured) return false;
    if (filters.trendingOnly && !p.trending) return false;
    return true;
  });
}
