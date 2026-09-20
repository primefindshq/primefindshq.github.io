// PRIME.FINDS entrance orchestration.
//
//   first ever visit     full WebGL sequence (~4.4s, skippable)
//   returning visitor    quick WebGL cut (~2s), same signature
//   same-session return  no entrance at all (internal navigation home)
//   reduced motion       opacity-only entrance (~1.5s), no movement
//   no WebGL / any error the original CSS entrance, untouched
//
// The overlay is made visible by a tiny inline script in <head> (see
// scripts/build.py) so the very first paint is already black -- no flash of
// the homepage before the entrance takes over. That script also carries a
// timed failsafe, so a JS failure can never leave the page covered.
//
// Accessibility: the overlay carries a real "Skip intro" button and a link to the
// Accessibility Statement (outside the hidden artwork). Any key, click or tap also
// skips. The reduced-motion path honors both the device setting and the in-page
// "Reduce motion" option. Nothing about the entrance's visuals or timing changed.
//
// Review helpers: ?intro=full | quick | off forces a variant, and
// ?introT=2.4 freezes the WebGL scene on a single frame of its timeline.

import { prefersReducedMotion } from '../core/a11y.js';

const VISITED_KEY = 'pf-visited';
const SESSION_KEY = 'pf-intro-session';
const LOGO_URL = '/assets/logo/wordmark.png';

function read(store, key) {
  try { return store.getItem(key); } catch { return null; }
}
function write(store, key, value) {
  try { store.setItem(key, value); } catch { /* private mode: entrance may replay, harmless */ }
}

export async function initBrandIntro() {
  const root = document.documentElement;
  const el = document.querySelector('[data-brand-intro]');
  const clearRoot = () => root.classList.remove('intro-pending', 'intro-active', 'intro-reveal');
  if (!el) { clearRoot(); return; }

  const params = new URLSearchParams(window.location.search);
  const force = params.get('intro');
  if (force === 'off' || (!force && read(sessionStorage, SESSION_KEY) === '1')) {
    el.remove();
    clearRoot();
    return;
  }

  // The device setting OR the in-page "Reduce motion" option (see core/a11y.js).
  const reduceMotion = prefersReducedMotion();
  const returning = force === 'full' ? false : force === 'quick' ? true : read(localStorage, VISITED_KEY) === '1';
  write(localStorage, VISITED_KEY, '1');
  write(sessionStorage, SESSION_KEY, '1');

  // From here on this module owns the entrance and its own timing.
  window.clearTimeout(window.__pfFs);
  document.body.classList.add('intro-lock');
  let ended = false;

  const end = () => {
    if (ended) return;
    ended = true;
    // If keyboard focus was on the overlay's own controls (Skip intro / Accessibility),
    // hand it to the page content so it is not lost when the overlay is removed.
    const focusWasInside = el.contains(document.activeElement);
    document.body.classList.remove('intro-lock');
    clearRoot();
    root.style.removeProperty('--intro-reveal-dur');
    el.remove();
    if (focusWasInside) document.getElementById('main-content')?.focus({ preventScroll: true });
  };

  // ---- Reduced motion: opacity only, no movement, still a considered entrance.
  if (reduceMotion) {
    el.classList.add('is-live', 'is-reduced');
    const still = el.querySelector('.brand-intro__still');
    still?.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 650, delay: 120, easing: 'ease-out', fill: 'forwards' });
    let soft = false;
    const softOut = () => {
      if (soft) return;
      soft = true;
      root.classList.remove('intro-active');
      const fade = el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 500, easing: 'ease-in-out', fill: 'forwards' });
      fade.onfinish = end;
      window.setTimeout(end, 700);
    };
    const t = window.setTimeout(softOut, 1400);
    el.addEventListener('click', () => { window.clearTimeout(t); softOut(); });
    window.addEventListener('keydown', () => { window.clearTimeout(t); softOut(); }, { once: true });
    return;
  }

  // ---- The original CSS entrance, kept as the fallback path.
  const runCssIntro = () => {
    el.classList.add('is-live', 'is-css', 'is-playing');
    if (returning) el.classList.add('is-quick');
    const totalMs = returning ? 720 : 1780;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      root.classList.remove('intro-active');
      el.classList.add('is-done');
      document.body.classList.remove('intro-lock');
      window.setTimeout(end, 700);
    };
    const timer = window.setTimeout(finish, totalMs);
    el.addEventListener('click', () => { window.clearTimeout(timer); finish(); });
    window.addEventListener('keydown', () => { window.clearTimeout(timer); finish(); }, { once: true });
  };

  // ---- WebGL entrance.
  const lite =
    window.matchMedia('(pointer: coarse)').matches ||
    Math.min(window.innerWidth, window.innerHeight) < 600 ||
    (navigator.hardwareConcurrency || 8) <= 4;
  const debugT = params.has('introT') ? parseFloat(params.get('introT')) : undefined;

  let scene = null;
  try {
    const canvas = el.querySelector('.brand-intro__canvas');
    const stalled = new Promise((_, reject) => window.setTimeout(() => reject(new Error('scene load stalled')), 4500));
    const { createIntroScene } = await Promise.race([import('./introScene.js'), stalled]);
    scene = await createIntroScene({
      canvas,
      logoUrl: LOGO_URL,
      quick: returning,
      lite,
      debugT,
      // The portal has begun to open: let the real homepage arrive through it.
      onReveal: (realSecs) => {
        root.classList.remove('intro-active');
        root.style.setProperty('--intro-reveal-dur', `${Math.max(0.5, realSecs).toFixed(2)}s`);
        root.classList.add('intro-reveal');
      },
      onDone: end,
    });
  } catch {
    scene = null;
  }

  if (!scene) {
    runCssIntro();
    return;
  }

  // First frame is drawn synchronously inside start(), before the overlay's
  // own black background is released to the canvas -- no flash of the page.
  scene.start();
  el.classList.add('is-live', 'is-gl');
  if (debugT !== undefined) {
    // Frozen review frame: past the portal, let the real homepage show through.
    if (debugT >= 3.1) root.classList.remove('intro-active');
    return;
  }

  const skip = () => scene.skip();
  el.addEventListener('click', skip);
  window.addEventListener('keydown', skip, { once: true });
}
