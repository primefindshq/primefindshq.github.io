// Measures each category tile's inline SVG icon path so the CSS
// stroke-draw hover (see components.css) can use its exact length instead
// of a guessed constant -- the icons are different shapes (a monitor, a
// gamepad, a percent sign), so one fixed dasharray would draw some too
// fast and clip others.

export function initCategoryIconDraw(root = document) {
  root.querySelectorAll('.category-tile__icon-path').forEach((path) => {
    if (path.style.getPropertyValue('--dash-len')) return;
    try {
      const len = Math.ceil(path.getTotalLength());
      path.style.setProperty('--dash-len', len);
    } catch {
      /* malformed path data would throw; leave the CSS fallback in place */
    }
  });
}
