// Loaded on every page. Wires up the shared chrome (header, mobile menu,
// search overlay, scroll-reveal) and fires the page_view analytics event.
import { initHeader } from './components/nav.js';
import { initSearchOverlay } from './components/searchOverlay.js';
import { initScrollReveal } from './components/reveal.js';
import { trackPageView } from './core/analytics.js';

document.addEventListener('DOMContentLoaded', () => {
  initHeader();
  initSearchOverlay();
  initScrollReveal();
  trackPageView();
});
