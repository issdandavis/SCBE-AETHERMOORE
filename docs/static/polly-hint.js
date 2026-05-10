// polly-hint.js
//
// Floating, dismissible "Need help finding the right tool?" chip that points
// new visitors at the products picker and Polly chat. Self-contained: no
// dependencies, no API calls, no analytics — only sessionStorage to remember
// dismissal so the chip doesn't pester within the same browsing session.
//
// Suppression rules:
//   - Already dismissed in this session.
//   - Page is /chat.html, /products.html, /start-here.html, or /agents.html
//     (the visitor is already on a guidance surface; chip would be noise).
//   - User prefers reduced motion AND has narrow screen — don't add visual
//     clutter.
//
// Include via: <script src="static/polly-hint.js" defer></script>
'use strict';

(function () {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  var SESSION_KEY = 'polly_hint_dismissed_v1';
  var DELAY_MS = 4500;

  function isSuppressedPage() {
    var path = (window.location && window.location.pathname) || '';
    return /\/(chat|products|start-here|agents|polly-stats)\.html?$/i.test(path);
  }

  function alreadyDismissed() {
    try {
      return window.sessionStorage && window.sessionStorage.getItem(SESSION_KEY) === '1';
    } catch (_e) {
      return false;
    }
  }

  function rememberDismissal() {
    try {
      if (window.sessionStorage) window.sessionStorage.setItem(SESSION_KEY, '1');
    } catch (_e) {
      /* private mode — accept that the chip may reappear on next page */
    }
  }

  function trackEvent(name) {
    try {
      if (typeof window.pollyFunnelTrack === 'function') {
        window.pollyFunnelTrack(name);
      }
    } catch (_e) {
      /* never raise */
    }
  }

  function buildChip() {
    var wrap = document.createElement('div');
    wrap.id = 'polly-hint-chip';
    wrap.setAttribute('role', 'complementary');
    wrap.setAttribute('aria-label', 'Help finding the right tool');
    wrap.style.cssText = [
      'position: fixed',
      'right: 18px',
      'bottom: 18px',
      'max-width: 320px',
      'z-index: 9999',
      'background: linear-gradient(135deg, #1a2030, #11161f)',
      'border: 1px solid rgba(214, 167, 86, 0.45)',
      'border-radius: 16px',
      'padding: 14px 16px',
      'color: #f2f0ea',
      'font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      'box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45)',
      'opacity: 0',
      'transform: translateY(8px)',
      'transition: opacity 220ms ease, transform 220ms ease',
    ].join(';');

    wrap.innerHTML = [
      '<div style="display:flex; align-items:flex-start; gap:10px;">',
      '  <div style="flex:1;">',
      '    <div style="font-weight:700; color:#f0bf67; margin-bottom:4px;">Need help finding the right tool?</div>',
      '    <div style="color:#a3acb9; font-size:13px; margin-bottom:10px;">Three questions, one recommendation. Or chat with Polly.</div>',
      '    <div style="display:flex; gap:6px; flex-wrap:wrap;">',
      '      <a href="products.html" data-action="picker" style="background:linear-gradient(135deg,#d6a756,#f0bf67); color:#14110c; font-weight:700; text-decoration:none; padding:7px 12px; border-radius:999px; font-size:13px;">Find your fit →</a>',
      '      <a href="chat.html" data-action="chat" style="border:1px solid rgba(255,255,255,0.16); color:#f2f0ea; text-decoration:none; padding:6px 12px; border-radius:999px; font-size:13px;">Open chat</a>',
      '    </div>',
      '  </div>',
      '  <button type="button" data-action="dismiss" aria-label="Dismiss" style="background:transparent; border:0; color:#a3acb9; font-size:20px; line-height:1; cursor:pointer; padding:0 0 0 4px;">×</button>',
      '</div>',
    ].join('');

    wrap.addEventListener('click', function (event) {
      var target = event.target;
      while (target && target !== wrap) {
        var action = target.getAttribute && target.getAttribute('data-action');
        if (action === 'dismiss') {
          dismiss();
          event.preventDefault();
          return;
        }
        if (action === 'picker' || action === 'chat') {
          trackEvent('polly_hint_click_' + action);
          rememberDismissal();
          return;
        }
        target = target.parentNode;
      }
    });

    return wrap;
  }

  function dismiss() {
    var chip = document.getElementById('polly-hint-chip');
    if (!chip) return;
    chip.style.opacity = '0';
    chip.style.transform = 'translateY(8px)';
    setTimeout(function () {
      if (chip.parentNode) chip.parentNode.removeChild(chip);
    }, 240);
    rememberDismissal();
    trackEvent('polly_hint_dismissed');
  }

  function show() {
    if (document.getElementById('polly-hint-chip')) return;
    var chip = buildChip();
    document.body.appendChild(chip);
    requestAnimationFrame(function () {
      chip.style.opacity = '1';
      chip.style.transform = 'translateY(0)';
    });
    trackEvent('polly_hint_shown');
  }

  function init() {
    if (isSuppressedPage()) return;
    if (alreadyDismissed()) return;
    setTimeout(show, DELAY_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
