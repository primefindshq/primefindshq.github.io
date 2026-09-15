// The signature entry sequence. A true first-ever visit (tracked in
// localStorage, so it survives across sessions/tabs) gets the full
// cinematic sequence; any later visit gets a short "quick" variant so the
// brand still shows up every session without taxing a returning visitor.
// Markup defaults to `display: none` in CSS, so any failure here just
// means the overlay never appears -- it can never block the page.

const VISITED_KEY = 'pf-visited';

function hasVisitedBefore() {
  try {
    return localStorage.getItem(VISITED_KEY) === '1';
  } catch {
    return false;
  }
}

function markVisited() {
  try {
    localStorage.setItem(VISITED_KEY, '1');
  } catch {
    /* private-mode storage can throw; worst case every visit plays the full intro */
  }
}

export function initBrandIntro() {
  const el = document.querySelector('[data-brand-intro]');
  if (!el) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  const isReturning = hasVisitedBefore();
  markVisited();

  document.body.classList.add('intro-lock');
  el.classList.add('is-playing');
  if (isReturning) el.classList.add('is-quick');

  const TOTAL_MS = isReturning ? 720 : 1780;
  let done = false;

  const finish = () => {
    if (done) return;
    done = true;
    el.classList.add('is-done');
    document.body.classList.remove('intro-lock');
    window.setTimeout(() => el.remove(), 700);
  };

  const timer = window.setTimeout(finish, TOTAL_MS);

  const skip = () => {
    window.clearTimeout(timer);
    finish();
  };
  el.addEventListener('click', skip);
  window.addEventListener('keydown', skip, { once: true });
}
