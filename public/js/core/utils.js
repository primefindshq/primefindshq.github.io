// Small, dependency-free helpers shared across the site.

export function formatPrice(price, currency = 'USD') {
  if (price == null) return 'Check price';
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(price);
  } catch {
    return `$${Number(price).toFixed(2)}`;
  }
}

export function formatDate(iso) {
  try {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function slugify(str) {
  return String(str)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '');
}

export function debounce(fn, delay = 200) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

/** Renders a 0-5 star rating as inline SVG markup (never relies on color alone: also prints the numeric value). */
export function renderStars(rating = 0, reviewCount = null) {
  const full = Math.round(rating);
  let stars = '';
  for (let i = 0; i < 5; i++) {
    const filled = i < full;
    stars += `<svg viewBox="0 0 20 20" width="13" height="13" fill="${filled ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><path d="M10 1.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>`;
  }
  const label = rating > 0
    ? `${rating.toFixed(1)} out of 5${reviewCount ? ` (${reviewCount.toLocaleString()} reviews)` : ''}`
    : 'Not yet rated';
  const extra = rating > 0
    ? `<span>${rating.toFixed(1)}</span>${reviewCount ? `<span class="text-faint">(${reviewCount.toLocaleString()})</span>` : ''}`
    : '<span class="text-faint">New</span>';
  return `<span class="rating" role="img" aria-label="${label}"><span class="stars">${stars}</span>${extra}</span>`;
}
