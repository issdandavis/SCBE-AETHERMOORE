/**
 * SCBE AI Bridge — Cash App Bridge
 *
 * Provides clean API for interacting with Cash App web:
 * - Read balance
 * - Read transactions
 * - Navigate to tax filing
 * - Read activity feed
 */

(function () {
  'use strict';

  const api = {
    getBalance() {
      const balanceEls = document.querySelectorAll('[data-testid*="balance"], .balance-amount');
      const balances = {};
      document.querySelectorAll('article, [role="listitem"]').forEach(el => {
        const text = el.textContent;
        if (text.includes('Cash') && text.includes('$')) {
          const match = text.match(/\$[\d,.]+/);
          if (match) balances.cash = match[0];
        }
      });
      // Try reading from the visible balance display
      const allText = document.body.innerText;
      const cashMatch = allText.match(/Cash\s*\$?([\d,.]+)/);
      const savingsMatch = allText.match(/Savings\s*\$?([\d,.]+)/);
      const stocksMatch = allText.match(/Stocks\s*\$?([\d,.]+)/);
      const btcMatch = allText.match(/Bitcoin\s*\$?([\d,.]+)/);
      return {
        cash: cashMatch?.[1] || 'unknown',
        savings: savingsMatch?.[1] || 'unknown',
        stocks: stocksMatch?.[1] || 'unknown',
        bitcoin: btcMatch?.[1] || 'unknown',
      };
    },

    getTransactions(limit = 20) {
      const txns = [];
      document.querySelectorAll('[data-testid*="transaction"], .transaction-item, tr').forEach((el, i) => {
        if (i >= limit) return;
        txns.push({
          text: el.textContent.trim().slice(0, 200),
          index: i,
        });
      });
      return txns;
    },

    navigateToTaxes() {
      window.location.href = 'https://cash.app/taxes/applet';
      return { ok: true };
    },

    navigateToActivity() {
      window.location.href = 'https://cash.app/account/activity';
      return { ok: true };
    },

    navigateToDocuments() {
      window.location.href = 'https://cash.app/account/documents/account-statements';
      return { ok: true };
    },
  };

  window.__scbe_cashapp = api;

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

  console.log('[SCBE Cash App Bridge] Ready');
})();
