// Loaded on every page. Wires up the shared chrome (header, mobile menu,
// search overlay, scroll-reveal) and fires the page_view analytics event.
import { initHeader } from './components/nav.js';
import { initSearchOverlay } from './components/searchOverlay.js';
import { initScrollReveal } from './components/reveal.js';
import { initBrandIntro } from './components/brandIntro.js';
import { initRails } from './components/rail.js';
import { initCardTilt } from './components/cardTilt.js';
import { initMagneticButtons } from './components/magneticButton.js';
import { initCategoryIconDraw } from './components/categoryIconDraw.js';
import { trackPageView } from './core/analytics.js';

document.addEventListener('DOMContentLoaded', () => {
  initBrandIntro();
  initHeader();
  initSearchOverlay();
  initScrollReveal();
  initRails();
  initCardTilt();
  initMagneticButtons();
  initCategoryIconDraw();
  trackPageView();
});
