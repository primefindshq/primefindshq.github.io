// Prev/next controls for horizontal product rails. The rail itself is a
// plain scroll-snap container (CSS-only, works without this script); this
// just makes the arrow buttons drive it and disables them at each end.

export function initRails(root = document) {
  root.querySelectorAll('[data-rail]').forEach((rail) => {
    const id = rail.id;
    const prevBtn = root.querySelector(`[data-rail-prev="${id}"]`);
    const nextBtn = root.querySelector(`[data-rail-next="${id}"]`);
    if (!prevBtn && !nextBtn) return;

    const step = () => {
      const item = rail.querySelector('.rail__item');
      return item ? item.getBoundingClientRect().width + 16 : rail.clientWidth * 0.8;
    };

    prevBtn?.addEventListener('click', () => rail.scrollBy({ left: -step(), behavior: 'smooth' }));
    nextBtn?.addEventListener('click', () => rail.scrollBy({ left: step(), behavior: 'smooth' }));

    const updateDisabled = () => {
      const max = rail.scrollWidth - rail.clientWidth;
      if (prevBtn) prevBtn.disabled = rail.scrollLeft <= 4;
      if (nextBtn) nextBtn.disabled = rail.scrollLeft >= max - 4;
    };
    rail.addEventListener('scroll', updateDisabled, { passive: true });
    updateDisabled();
  });
}
