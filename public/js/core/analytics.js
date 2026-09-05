// ---------------------------------------------------------------------------
// Analytics abstraction.
//
// The rest of the app never talks to Google Analytics / any vendor SDK
// directly — it calls `track(eventName, payload)` from this module. Wiring
// up a real provider later means editing ONLY the `dispatch()` function
// below (e.g. call `gtag('event', ...)` or `posthog.capture(...)`), with
// zero changes anywhere else in the codebase.
//
// Configure a provider by setting `window.__PRIME_FINDS_ANALYTICS_CONFIG`
// (e.g. injected server-side from an env var) before this module loads:
//   window.__PRIME_FINDS_ANALYTICS_CONFIG = { provider: 'ga4', id: 'G-XXXX' };
// Until that's set, events simply no-op (and log to console in dev).
// ---------------------------------------------------------------------------

const IS_DEV = ['localhost', '127.0.0.1'].includes(window.location.hostname);

function getConfig() {
  return window.__PRIME_FINDS_ANALYTICS_CONFIG || { provider: 'none' };
}

function dispatch(eventName, payload) {
  const config = getConfig();

  switch (config.provider) {
    case 'ga4':
      if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, payload);
      }
      break;
    case 'plausible':
      if (typeof window.plausible === 'function') {
        window.plausible(eventName, { props: payload });
      }
      break;
    default:
      // No provider configured yet — this is expected pre-launch.
      break;
  }

  if (IS_DEV) {
    // eslint-disable-next-line no-console
    console.debug('[analytics]', eventName, payload);
  }
}

/** Canonical event names the rest of the app is allowed to fire. Keep this list authoritative. */
export const EVENTS = {
  PAGE_VIEW: 'page_view',
  PRODUCT_VIEW: 'product_view',
  CATEGORY_VIEW: 'category_view',
  SEARCH: 'search',
  FILTER_USED: 'filter_used',
  AFFILIATE_CLICK: 'affiliate_click',
  EXTERNAL_LINK_CLICK: 'external_link_click',
};

export function track(eventName, payload = {}) {
  dispatch(eventName, { ...payload, timestamp: new Date().toISOString() });
}

export function trackPageView(extra = {}) {
  track(EVENTS.PAGE_VIEW, { path: window.location.pathname, ...extra });
}
