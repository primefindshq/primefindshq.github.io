// Accessibility preferences: text size, high contrast, reduced motion.
//
// The choices live in localStorage under one key and are mirrored onto <html>
// as data attributes (data-text / data-contrast / data-motion), which the CSS in
// css/a11y.css keys off. An inline script in <head> (see scripts/build.py) applies
// them before first paint, so a returning visitor never sees a flash of the wrong
// size or contrast. Nothing here is sent anywhere.

export const STORAGE_KEY = 'pf-a11y';
// Percent of the browser's own base font size. Everything in the site is rem-based,
// so scaling <html> scales the whole page and stays relative to the user's setting.
export const TEXT_SCALES = [100, 112.5, 125, 150, 175];

const root = document.documentElement;
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

const clampStep = (n) => Math.min(TEXT_SCALES.length - 1, Math.max(0, Number(n) | 0));

export function readSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return { text: clampStep(saved.text), contrast: !!saved.contrast, motion: !!saved.motion };
  } catch {
    return { text: 0, contrast: false, motion: false };
  }
}

export function saveSettings(settings) {
  try {
    if (!settings.text && !settings.contrast && !settings.motion) localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    /* storage blocked: the choice still applies for this page view */
  }
}

export function applySettings(settings) {
  if (settings.text) root.setAttribute('data-text', String(settings.text));
  else root.removeAttribute('data-text');
  if (settings.contrast) root.setAttribute('data-contrast', 'high');
  else root.removeAttribute('data-contrast');
  if (settings.motion) root.setAttribute('data-motion', 'reduce');
  else root.removeAttribute('data-motion');
  document.dispatchEvent(new CustomEvent('pf:a11y-change', { detail: settings }));
}

/**
 * Keeps an `text-large` class on <html> whenever the root font is bigger than the
 * default (our text-size option, or the browser / phone's own larger-text setting).
 * The CSS uses it to make room in tight spots such as the header.
 */
export function watchTextScale() {
  const update = () => {
    root.classList.toggle('text-large', parseFloat(getComputedStyle(root).fontSize) > 17.5);
  };
  update();
  window.addEventListener('resize', update);
  document.addEventListener('pf:a11y-change', update);
}

/** True when the device asks for reduced motion OR the visitor switched it on here. */
export function prefersReducedMotion() {
  return motionQuery.matches || root.getAttribute('data-motion') === 'reduce';
}

/** True when the device itself is already asking for reduced motion. */
export function deviceReducesMotion() {
  return motionQuery.matches;
}
