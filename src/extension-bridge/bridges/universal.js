/**
 * SCBE AI Bridge — Universal Bridge
 *
 * Runs on all pages. Provides basic capabilities:
 * - Read page text/HTML
 * - Fill forms
 * - Click elements
 * - Read page metadata
 * - Expose bridge status to Playwright via window.__scbe
 */

(function () {
  'use strict';

  const api = {
    // Get page text content
    getPageText() {
      return document.body.innerText.slice(0, 50000);
    },

    // Get page metadata
    getPageMeta() {
      return {
        title: document.title,
        url: window.location.href,
        domain: window.location.hostname,
        description: document.querySelector('meta[name="description"]')?.content || '',
        favicon: document.querySelector('link[rel="icon"]')?.href || '',
      };
    },

    // Find and click an element by text content
    clickByText(text) {
      const els = document.querySelectorAll('button, a, [role="button"], input[type="submit"]');
      for (const el of els) {
        if (el.textContent.trim().includes(text)) {
          el.click();
          return { ok: true, tag: el.tagName, text: el.textContent.trim().slice(0, 50) };
        }
      }
      return { ok: false, error: `No element with text "${text}" found` };
    },

    // Fill an input by label text
    fillByLabel(labelText, value) {
      const labels = document.querySelectorAll('label');
      for (const label of labels) {
        if (label.textContent.includes(labelText)) {
          const input = label.querySelector('input, textarea, select') ||
                       document.getElementById(label.getAttribute('for'));
          if (input) {
            input.focus();
            input.value = value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return { ok: true };
          }
        }
      }
      return { ok: false, error: `No input with label "${labelText}" found` };
    },

    // Get all form fields on the page
    getFormFields() {
      const fields = [];
      document.querySelectorAll('input, textarea, select').forEach((el, i) => {
        const label = el.closest('label')?.textContent ||
                     document.querySelector(`label[for="${el.id}"]`)?.textContent ||
                     el.getAttribute('aria-label') ||
                     el.getAttribute('placeholder') || '';
        fields.push({
          index: i,
          tag: el.tagName.toLowerCase(),
          type: el.type || '',
          name: el.name || '',
          label: label.trim().slice(0, 60),
          value: el.value?.slice(0, 100) || '',
        });
      });
      return fields;
    },

    // Scroll to bottom
    scrollToBottom() {
      window.scrollTo(0, document.body.scrollHeight);
      return true;
    },

    // Scroll to top
    scrollToTop() {
      window.scrollTo(0, 0);
      return true;
    },

    // Take a snapshot of visible text (lightweight alternative to full DOM)
    snapshot() {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const lines = [];
      let node;
      while ((node = walker.nextNode()) && lines.length < 200) {
        const text = node.textContent.trim();
        if (text.length > 2) lines.push(text);
      }
      return lines.join('\n').slice(0, 10000);
    },

    // Check if SCBE bridge is loaded
    status() {
      return {
        bridge: 'universal',
        version: '0.1.0',
        url: window.location.href,
        colab: !!window.__scbe_colab,
        cashapp: !!window.__scbe_cashapp,
      };
    },
  };

  window.__scbe = api;

  // Handle commands from background script
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type !== 'bridge-command') return;
    const fn = api[msg.action];
    if (!fn) {
      sendResponse({ ok: false, error: `Unknown action: ${msg.action}` });
      return;
    }
    try {
      const result = fn(...(msg.params || []));
      sendResponse({ ok: true, result });
    } catch (e) {
      sendResponse({ ok: false, error: e.message });
    }
  });

  console.log('[SCBE Universal Bridge] Ready on', window.location.hostname);
})();
