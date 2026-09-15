// Header scroll state + the site index overlay (the single, universal way
// to browse PRIME.FINDS -- there is no separate desktop nav to keep in
// sync with this). Shared across every page.

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
      // then comes back the instant you're looking for it again.
      const scrollingDown = y > lastY && y > 160;
      header.classList.toggle('is-hidden', scrollingDown);
      lastY = y;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(apply);
      }
    }, { passive: true });
    apply();
  }

  const toggle = document.querySelector('[data-index-toggle]');
  const menu = document.querySelector('[data-index-panel]');
  const closeBtn = document.querySelector('[data-index-close]');
  if (!toggle || !menu) return;

  const closeMenu = () => {
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
  };
  const openMenu = () => {
    menu.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('menu-open');
    menu.querySelector('a')?.focus({ preventScroll: true });
  };

  toggle.addEventListener('click', () => {
    const isOpen = menu.classList.contains('is-open');
    isOpen ? closeMenu() : openMenu();
  });
  closeBtn?.addEventListener('click', closeMenu);
  menu.querySelectorAll('a').forEach((a) => a.addEventListener('click', closeMenu));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menu.classList.contains('is-open')) closeMenu();
  });
}
