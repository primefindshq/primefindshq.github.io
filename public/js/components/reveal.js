// Scroll-reveal: adds `.is-visible` to any [data-reveal] element once it
// enters the viewport. Respects prefers-reduced-motion by doing nothing
// (elements are already visible by default via CSS in that case).

export function initScrollReveal(root = document) {
  const els = root.querySelectorAll('[data-reveal]');
  if (!els.length) return;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const delay = Number(el.dataset.revealDelay || 0);
          setTimeout(() => el.classList.add('is-visible'), delay);
          observer.unobserve(el);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  els.forEach((el) => observer.observe(el));
}
