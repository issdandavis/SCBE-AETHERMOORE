// src/extension/content.js
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    const text = extractVisibleText();
    sendResponse({
      url: window.location.href,
      title: document.title,
      text: text,
    });
  }
  return true;
});

function extractVisibleText() {
  const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'IFRAME']);
  const MAX_LENGTH = 100_000;

  let text = '';
  const walker = document.createTreeWalker(
    document.body || document.documentElement,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        if (SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
        if (parent.hidden || parent.getAttribute('aria-hidden') === 'true') {
          return NodeFilter.FILTER_REJECT;
        }
        const style = getComputedStyle(parent);
        if (style.display === 'none' || style.visibility === 'hidden') {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  while (walker.nextNode()) {
    const value = walker.currentNode.nodeValue.trim();
    if (value) {
      text += value + ' ';
      if (text.length > MAX_LENGTH) break;
    }
  }

  return text.slice(0, MAX_LENGTH).trim();
}
