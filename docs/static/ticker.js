/**
 * @file ticker.js
 * MARKETS: reads from /research-feed.json (Yahoo Finance via GH Action).
 * No browser-side API keys. 5-minute poll.
 * Replaces a previous version that called Finnhub directly with an empty token.
 */
(function () {
  "use strict";

  var FEED = "/research-feed.json";
  var POLL = 5 * 60 * 1000;

  function updateEl(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function applyClass(id, chg) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = "ch " + (chg > 0.05 ? "up" : chg < -0.05 ? "dn" : "flat");
  }

  function renderMarkets(markets) {
    if (!markets) return;
    var symbols = Object.keys(markets);
    symbols.forEach(function (sym) {
      var d = markets[sym];
      if (!d || d.price == null) return;
      var priceStr =
        sym === "BTC"
          ? "$" + Math.round(d.price).toLocaleString()
          : "$" + d.price.toFixed(2);
      updateEl("mk-" + sym, priceStr);
      // Support both naming conventions used across pages
      updateEl("tk-" + sym + "-price", priceStr);

      if (d.chg != null) {
        var sign = d.chg >= 0 ? "+" : "";
        var chgStr = sign + d.chg.toFixed(2) + "%";
        updateEl("mk-" + sym + "-c", chgStr);
        updateEl("tk-" + sym + "-chg", chgStr);
        applyClass("mk-" + sym + "-c", d.chg);
        applyClass("tk-" + sym + "-chg", d.chg);
      }
    });
  }

  function load() {
    fetch(FEED + "?_=" + Date.now(), { cache: "no-store" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (data && data.markets) renderMarkets(data.markets);
      })
      .catch(function (e) {
        if (typeof console !== "undefined") console.warn("[ticker]", e);
      });
  }

  load();
  setInterval(load, POLL);
})();
