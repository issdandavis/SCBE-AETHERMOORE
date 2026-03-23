/**
 * @file address-bar.js
 * @module desktop/renderer/address-bar
 *
 * URL bar logic: detects whether input is a URL or search query,
 * dispatches navigation to the main process via the addressBarBridge preload.
 */

const urlInput = document.getElementById('url-input');
const btnBack = document.getElementById('btn-back');
const btnForward = document.getElementById('btn-forward');
const btnReload = document.getElementById('btn-reload');

// Default search engine — DuckDuckGo (no API key needed, privacy-first)
const SEARCH_URL = 'https://duckduckgo.com/?q=';

/**
 * Determine if the input string looks like a navigable URL.
 * Returns the normalized URL if it is, or null if it should be treated as a search query.
 */
function parseInput(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  // Already has a protocol
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  // Looks like a domain (contains a dot and no spaces)
  if (/^[^\s]+\.[a-z]{2,}(\/.*)?$/i.test(trimmed)) {
    return 'https://' + trimmed;
  }

  // localhost or IP with optional port
  if (/^(localhost|(\d{1,3}\.){3}\d{1,3})(:\d+)?(\/.*)?$/i.test(trimmed)) {
    return 'http://' + trimmed;
  }

  // Treat as a search query
  return SEARCH_URL + encodeURIComponent(trimmed);
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    const url = parseInput(urlInput.value);
    if (url) {
      window.addressBarBridge.navigate(url);
      urlInput.blur();
    }
  }
});

// Select all text on focus (like a real browser address bar)
urlInput.addEventListener('focus', () => {
  requestAnimationFrame(() => urlInput.select());
});

btnBack.addEventListener('click', () => {
  window.addressBarBridge.goBack();
});

btnForward.addEventListener('click', () => {
  window.addressBarBridge.goForward();
});

btnReload.addEventListener('click', () => {
  window.addressBarBridge.reload();
});

// ---------------------------------------------------------------------------
// IPC listeners — main process pushes navigation state updates
// ---------------------------------------------------------------------------

window.addressBarBridge.onNavigationUpdate((data) => {
  // Update the URL bar with the current page URL
  if (!urlInput.matches(':focus')) {
    urlInput.value = data.url || '';
  }

  // Update navigation button states
  btnBack.disabled = !data.canGoBack;
  btnForward.disabled = !data.canGoForward;

  // Update window title
  if (data.title) {
    document.title = data.title + ' - AetherBrowser';
  }
});

window.addressBarBridge.onFocusAddressBar(() => {
  urlInput.focus();
  urlInput.select();
});
