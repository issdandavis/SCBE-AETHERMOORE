/* Polly funnel beacons — operator-only telemetry for buyer and service pages.
 *
 * Fires named events to /v1/polly/funnel so the operator dashboard can
 * see fall-off per stage. Designed to be drop-in: include this script
 * once on a page, and call PollyFunnel.fire('arrival') etc.
 *
 * Storage: NO cookies, NO third-party requests. Session id lives in
 * sessionStorage (per-tab, per-domain), opaque random hex, expires when
 * the tab closes. Page identity is derived from the file path so the
 * caller doesn't have to pass it.
 *
 * Failure mode: silent. A funnel beacon never blocks a UI action and
 * never surfaces an error to the user. fetch() failures are swallowed.
 *
 * Anti-spam: dedupes the same {event,page} within 1500 ms (rage-click
 * guard). The server also rate-limits at 60/min per IP under the
 * `feedback` bucket.
 */
(function () {
  'use strict';

  var DEFAULT_API_BASE = 'https://scbe-agent-bridge-vercel.vercel.app';
  var DEDUP_WINDOW_MS = 1500;

  function getApiBase() {
    var override = window.POLLY_VERCEL_BASE;
    var base = (override || DEFAULT_API_BASE).replace(/\/$/, '');
    return base + '/v1/polly/funnel';
  }

  function pageId() {
    var p = (location.pathname || '').toLowerCase();
    if (p.indexOf('governance-snapshot') !== -1) return 'governance-snapshot';
    // Variant pages MUST be detected before the generic /hire match,
    // otherwise hire-b.html would funnel into the same bucket as /hire
    // and the A/B comparison would be impossible.
    if (p.indexOf('hire-b') !== -1) return 'hire-b';
    if (p.indexOf('/hire') !== -1) return 'hire';
    if (p.indexOf('hire.html') !== -1) return 'hire';
    if (p.indexOf('polly-stats') !== -1) return 'polly-stats';
    // Fallback: last path segment, sans extension. Bounded length matches server.
    var seg = (p.split('/').pop() || 'unknown').replace(/\.html?$/, '') || 'unknown';
    return seg.slice(0, 80);
  }

  function getSession() {
    try {
      var key = 'polly_funnel_sid';
      var existing = window.sessionStorage.getItem(key);
      if (existing) return existing;
      var rnd = new Uint8Array(8);
      (window.crypto || {}).getRandomValues
        ? window.crypto.getRandomValues(rnd)
        : (function () {
            for (var i = 0; i < rnd.length; i++) rnd[i] = Math.floor(Math.random() * 256);
          })();
      var sid =
        'sess-' +
        Array.from(rnd, function (b) {
          return b.toString(16).padStart(2, '0');
        }).join('');
      window.sessionStorage.setItem(key, sid);
      return sid;
    } catch (_e) {
      // Private mode or storage disabled — generate a one-shot id.
      return 'sess-anon-' + Date.now().toString(36);
    }
  }

  // {key: lastFiredMs} for dedup.
  var lastFire = {};

  function shouldFire(key, now) {
    var prev = lastFire[key] || 0;
    if (now - prev < DEDUP_WINDOW_MS) return false;
    lastFire[key] = now;
    return true;
  }

  function fire(event, meta) {
    var page = pageId();
    var key = page + '|' + event;
    var now = Date.now();
    if (!shouldFire(key, now)) return Promise.resolve({ skipped: 'dedup' });
    var body = {
      event: event,
      page: page,
      session: getSession(),
      meta: meta || null,
    };
    try {
      // Use fetch with keepalive so beacons survive page navigation
      // (e.g. a CTA click that immediately navigates away).
      return fetch(getApiBase(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        keepalive: true,
      }).catch(function () {
        return { error: true };
      });
    } catch (_e) {
      return Promise.resolve({ error: true });
    }
  }

  function attr(el, name) {
    return (el && el.getAttribute && el.getAttribute(name)) || '';
  }

  function inferClickEvent(el) {
    var explicit = attr(el, 'data-funnel-event');
    if (explicit) return explicit.toLowerCase();
    var href = attr(el, 'href').toLowerCase();
    if (href.indexOf('buy.stripe.com') !== -1 || href.indexOf('#cash-app') !== -1) {
      return 'cta_click_buy';
    }
    if (href.indexOf('mailto:') === 0) return 'cta_click_email';
    if (href.indexOf('chat.html') !== -1 || href.indexOf('#chat') !== -1) return 'cta_click_chat';
    return '';
  }

  function clickMeta(el) {
    var label = attr(el, 'data-funnel-label') || (el.textContent || '').trim();
    var href = attr(el, 'href');
    return {
      label: label.slice(0, 96),
      href: href.slice(0, 180),
    };
  }

  function autoAttachClicks() {
    document.addEventListener(
      'click',
      function (ev) {
        var target = ev.target && ev.target.closest ? ev.target.closest('a,button') : null;
        if (!target) return;
        var event = inferClickEvent(target);
        if (!event) return;
        fire(event, clickMeta(target));
      },
      { capture: true }
    );
  }

  // Auto-attach scroll thresholds. Calls scroll_50 once and scroll_90 once
  // when the corresponding doc-fraction is reached. No-op on pages too
  // short to scroll (avoids firing on widget-only modals).
  function autoAttachScroll() {
    var fired50 = false;
    var fired90 = false;
    function onScroll() {
      var doc = document.documentElement;
      var scrolled = (window.pageYOffset || doc.scrollTop || 0) + window.innerHeight;
      var height = Math.max(doc.scrollHeight || 0, document.body ? document.body.scrollHeight : 0);
      if (height <= window.innerHeight * 1.2) return; // not really scrollable
      var pct = scrolled / height;
      if (!fired50 && pct >= 0.5) {
        fired50 = true;
        fire('scroll_50');
      }
      if (!fired90 && pct >= 0.9) {
        fired90 = true;
        fire('scroll_90');
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function autoAttachArrival() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        fire('arrival');
        autoAttachScroll();
        autoAttachClicks();
      });
    } else {
      fire('arrival');
      autoAttachScroll();
      autoAttachClicks();
    }
  }

  // Public surface — small and stable so callers can sprinkle into
  // existing JS without coupling to internals.
  var api = {
    fire: fire,
    pageId: pageId,
    session: getSession,
  };
  window.PollyFunnel = api;

  // Auto-fire arrival + scroll thresholds unless the page sets
  // window.POLLY_FUNNEL_AUTO = false before this script loads.
  if (window.POLLY_FUNNEL_AUTO !== false) {
    autoAttachArrival();
  }
})();
