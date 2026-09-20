// Shared behaviour for the site's modal dialogs (site menu, search, accessibility
// options): make everything behind the open dialog inert, and give focus back to
// where it came from when it closes.
//
// `inert` removes the background from the tab order AND from the accessibility
// tree in one step, which is exactly what a modal dialog needs -- keyboard focus
// cannot wander off into the page behind it, and a screen reader cannot read it.

/**
 * Makes every other top-level element of <body> inert while `dialogEl` is open.
 * Returns a function that undoes it.
 */
export function lockBackground(dialogEl) {
  const changed = [];
  Array.from(document.body.children).forEach((el) => {
    if (el === dialogEl || el.contains(dialogEl)) return;
    if (el.tagName === 'SCRIPT' || el.tagName === 'NOSCRIPT' || el.tagName === 'STYLE') return;
    if (el.hasAttribute('inert')) return;
    el.setAttribute('inert', '');
    changed.push(el);
  });
  return () => changed.forEach((el) => el.removeAttribute('inert'));
}

/**
 * Focus `el` if it is still in the page; otherwise fall back. When nothing specific had
 * focus (some browsers, notably Safari, do not focus a button on click, so the opener is
 * <body>), the trigger control is used, so keyboard users never lose their place.
 */
export function restoreFocus(el, fallback) {
  const target = el && el !== document.body && document.contains(el) ? el : fallback;
  target?.focus?.({ preventScroll: true });
}
