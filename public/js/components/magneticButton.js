// A restrained magnetic pull on primary CTAs -- the button leans a few
// pixels toward the cursor as it approaches, and releases with a spring
// back to rest. Reserved for .btn--primary only: applying this to every
// button on the page is exactly the "everything is moving" failure mode:
// the brief asked for the CTA to feel expensive, not for every control to
// wobble. transform-only pull region measured off the button itself, so no
// extra listeners on ancestors and nothing to clean up on unrelated moves.

import { prefersReducedMotion } from '../core/a11y.js';

const PULL_RADIUS = 90;
const MAX_PULL = 10;

export function initMagneticButtons(root = document) {
  const supportsHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (!supportsHover) return;

  root.querySelectorAll('.btn--primary').forEach((btn) => {
    let ticking = false;
    let pendingX = 0;
    let pendingY = 0;
    let active = false;

    const apply = () => {
      ticking = false;
      btn.style.setProperty('--mag-x', `${pendingX}px`);
      btn.style.setProperty('--mag-y', `${pendingY}px`);
    };

    const onMove = (e) => {
      if (prefersReducedMotion()) {
        if (active) reset();
        return;
      }
      const rect = btn.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.hypot(dx, dy);
      const within = dist < rect.width / 2 + PULL_RADIUS;

      if (within) {
        active = true;
        const pull = Math.min(1, 1 - dist / (rect.width / 2 + PULL_RADIUS));
        pendingX = (dx / dist || 0) * pull * MAX_PULL;
        pendingY = (dy / dist || 0) * pull * MAX_PULL;
      } else if (active) {
        active = false;
        pendingX = 0;
        pendingY = 0;
      } else {
        return;
      }
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(apply);
      }
    };

    const reset = () => {
      active = false;
      btn.style.setProperty('--mag-x', '0px');
      btn.style.setProperty('--mag-y', '0px');
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    btn.addEventListener('pointerleave', reset);
  });
}
