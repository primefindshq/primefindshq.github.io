// Cursor-aware tilt for product cards -- a few degrees of rotateX/rotateY
// driven by pointer position, so a card reads as an object with presence
// rather than a flat rectangle. transform-only (GPU), rAF-throttled, and
// gated off entirely for touch and reduced-motion, where it would either
// never fire correctly or actively fight the user's preference.
//
// Listeners attach per-card rather than delegated from a root: `pointerleave`
// fires on whichever element the pointer's bounding box actually left, so a
// delegated capture-phase listener would fire (and wrongly reset the tilt)
// every time the cursor crossed from the image into the text area of the
// SAME card, not just when it left the card entirely.

import { prefersReducedMotion } from '../core/a11y.js';

const MAX_DEG = 5;

export function initCardTilt(root = document) {
  const supportsHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (!supportsHover) return;

  root.querySelectorAll('.product-card').forEach((card) => {
    let ticking = false;
    let pendingX = 0;
    let pendingY = 0;

    const apply = () => {
      ticking = false;
      card.style.setProperty('--tilt-y', `${pendingX * MAX_DEG}deg`);
      card.style.setProperty('--tilt-x', `${-pendingY * MAX_DEG}deg`);
    };

    card.addEventListener('pointermove', (e) => {
      // Checked on every move so the in-page "Reduce motion" option takes effect immediately.
      if (prefersReducedMotion()) return;
      const rect = card.getBoundingClientRect();
      pendingX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pendingY = ((e.clientY - rect.top) / rect.height) * 2 - 1;
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(apply);
      }
    });

    card.addEventListener('pointerleave', () => {
      card.style.setProperty('--tilt-x', '0deg');
      card.style.setProperty('--tilt-y', '0deg');
    });
  });
}
