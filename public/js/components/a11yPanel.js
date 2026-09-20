// The accessibility options panel. Every control changes something real:
//   Text size      -> data-text on <html>   (css/a11y.css scales the root font size)
//   High contrast  -> data-contrast on <html> (colour tokens swapped)
//   Reduce motion  -> data-motion on <html>  (mirrors prefers-reduced-motion in CSS;
//                                             JS animation gates read the same flag)
// It is a modal dialog: focus moves in, the page behind is inert, Escape or the
// close button (or a click outside) closes it, and focus returns to the trigger.
import {
  TEXT_SCALES,
  readSettings,
  saveSettings,
  applySettings,
  deviceReducesMotion,
} from '../core/a11y.js';
import { lockBackground, restoreFocus } from '../core/dialogs.js';

export function initA11yPanel() {
  const panel = document.querySelector('[data-a11y-panel]');
  const toggle = document.querySelector('[data-a11y-toggle]');
  if (!panel || !toggle) return;

  const closeBtn = panel.querySelector('[data-a11y-close]');
  const downBtn = panel.querySelector('[data-a11y-text-down]');
  const upBtn = panel.querySelector('[data-a11y-text-up]');
  const valueEl = panel.querySelector('[data-a11y-text-value]');
  const contrastSwitch = panel.querySelector('[data-a11y-contrast]');
  const motionSwitch = panel.querySelector('[data-a11y-motion]');
  const motionHint = panel.querySelector('[data-a11y-motion-hint]');
  const resetBtn = panel.querySelector('[data-a11y-reset]');
  const status = panel.querySelector('[data-a11y-status]');

  const settings = readSettings();
  let unlock = null;
  let opener = null;

  const announce = (msg) => {
    if (!status) return;
    status.textContent = '';
    // Re-set on the next frame so repeating the same message is announced again.
    requestAnimationFrame(() => { status.textContent = msg; });
  };

  const sync = () => {
    const pct = TEXT_SCALES[settings.text];
    valueEl.textContent = `${pct}%`;
    downBtn.disabled = settings.text === 0;
    upBtn.disabled = settings.text === TEXT_SCALES.length - 1;
    contrastSwitch.setAttribute('aria-checked', String(settings.contrast));
    // If the device already asks for reduced motion, the switch is shown on and locked:
    // the visitor's OS-level choice always wins and cannot be undone from here.
    const deviceReduces = deviceReducesMotion();
    motionSwitch.setAttribute('aria-checked', String(deviceReduces || settings.motion));
    motionSwitch.disabled = deviceReduces;
    if (motionHint) {
      motionHint.textContent = deviceReduces
        ? 'Your device is already set to reduce motion, so this is on.'
        : 'Calmer transitions and a simplified intro.';
    }
  };

  const commit = (msg) => {
    saveSettings(settings);
    applySettings(settings);
    sync();
    // A disabled button cannot hold focus: if the button just used reached its limit,
    // hand focus to its partner so keyboard users are never dropped out of the dialog.
    const active = document.activeElement;
    if (active && active.disabled && panel.contains(active)) {
      (active === downBtn ? upBtn : downBtn).focus({ preventScroll: true });
    }
    if (msg) announce(msg);
  };

  const open = () => {
    if (panel.classList.contains('is-open')) return;
    opener = document.activeElement;
    panel.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
    unlock = lockBackground(panel);
    sync();
    // Focus the first control that is usable (the size buttons may be disabled at the ends).
    const first = panel.querySelector('.a11y-panel__body button:not([disabled])');
    (first || panel).focus({ preventScroll: true });
  };

  const close = ({ restore = true } = {}) => {
    if (!panel.classList.contains('is-open')) return;
    panel.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    unlock?.();
    unlock = null;
    if (restore) restoreFocus(opener, toggle);
  };

  toggle.addEventListener('click', () => (panel.classList.contains('is-open') ? close() : open()));
  closeBtn?.addEventListener('click', () => close());
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panel.classList.contains('is-open')) {
      e.preventDefault();
      close();
    }
  });
  // A click outside the panel dismisses it (the page behind is inert, so this only
  // fires for clicks on the page background, never for a control).
  document.addEventListener('pointerdown', (e) => {
    if (!panel.classList.contains('is-open')) return;
    if (panel.contains(e.target) || toggle.contains(e.target)) return;
    close({ restore: false });
  });

  downBtn.addEventListener('click', () => {
    if (settings.text > 0) {
      settings.text -= 1;
      commit(`Text size ${TEXT_SCALES[settings.text]} percent`);
    }
  });
  upBtn.addEventListener('click', () => {
    if (settings.text < TEXT_SCALES.length - 1) {
      settings.text += 1;
      commit(`Text size ${TEXT_SCALES[settings.text]} percent`);
    }
  });
  contrastSwitch.addEventListener('click', () => {
    settings.contrast = !settings.contrast;
    commit(`High contrast ${settings.contrast ? 'on' : 'off'}`);
  });
  motionSwitch.addEventListener('click', () => {
    if (motionSwitch.disabled) return;
    settings.motion = !settings.motion;
    commit(`Reduce motion ${settings.motion ? 'on' : 'off'}`);
  });
  resetBtn.addEventListener('click', () => {
    settings.text = 0;
    settings.contrast = false;
    settings.motion = false;
    commit('All accessibility options reset');
  });

  applySettings(settings);
  sync();
}
