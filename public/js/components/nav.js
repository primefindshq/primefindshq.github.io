// Header scroll state + the site index overlay (the single, universal way
// to browse PRIME.FINDS -- there is no separate desktop nav to keep in
// sync with this). Shared across every page.
//
// The index is a modal dialog: when it opens, focus moves into it and the page
// behind becomes inert; Escape or the close button closes it and focus goes back
// to the control that opened it.
import { lockBackground, restoreFocus } from '../core/dialogs.js';

export function initHeader() {
  const header = document.querySelector('.site-header');
  if (header) {
    let lastY = window.scrollY;
    let ticking = false;

    const apply = () => {
      ticking = false;
      const y = window.scrollY;
      header.classList.toggle('is-scrolled', y > 8);
      // Hide on the way down (once there's real distance from the top, so
      // it doesn't flicker while reading the hero), reveal on the way up --
      // the header gets out of the way while scrolling toward something,
      // then comes back the instant you're looking for it again. It never
      // hides while keyboard focus is inside it (that would put the focused
      // control off-screen).
      const scrollingDown = y > lastY && y > 160 && !header.contains(document.activeElement);
      header.classList.toggle('is-hidden', scrollingDown);
      lastY = y;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(apply);
      }
    }, { passive: true });
    header.addEventListener('focusin', () => header.classList.remove('is-hidden'));
    apply();
  }

  const toggle = document.querySelector('[data-index-toggle]');
  const menu = document.querySelector('[data-index-panel]');
  const closeBtn = document.querySelector('[data-index-close]');
  if (!toggle || !menu) return;

  let unlock = null;
  let opener = null;

  const closeMenu = ({ restore = true } = {}) => {
    if (!menu.classList.contains('is-open')) return;
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
    unlock?.();
    unlock = null;
    if (restore) restoreFocus(opener, toggle);
  };
  const openMenu = () => {
    opener = document.activeElement;
    menu.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('menu-open');
    unlock = lockBackground(menu);
    menu.querySelector('a')?.focus({ preventScroll: true });
  };

  toggle.addEventListener('click', () => {
    menu.classList.contains('is-open') ? closeMenu() : openMenu();
  });
  closeBtn?.addEventListener('click', () => closeMenu());
  // Following a link inside the menu leaves the page (or jumps within it), so focus
  // is not pulled back to the toggle in that case.
  menu.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => closeMenu({ restore: false })));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menu.classList.contains('is-open')) closeMenu();
  });
}
