// src/extension/content.js
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    const text = extractVisibleText();
    sendResponse({
      url: window.location.href,
      title: document.title,
      text: text,
      headings: extractHeadings(),
      links: extractLinks(),
      buttons: extractButtons(),
      forms: extractForms(),
      selection: window.getSelection()?.toString().trim() || '',
      pageType: inferPageType(),
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

function extractHeadings() {
  return Array.from(document.querySelectorAll('h1, h2, h3'))
    .slice(0, 20)
    .map((el) => ({
      level: el.tagName,
      text: el.textContent?.trim() || '',
    }))
    .filter((row) => row.text);
}

function extractLinks() {
  return Array.from(document.querySelectorAll('a[href]'))
    .slice(0, 40)
    .map((el) => ({
      text: (el.textContent || '').trim(),
      href: el.href || '',
    }))
    .filter((row) => row.href);
}

function extractButtons() {
  return Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'))
    .slice(0, 20)
    .map((el) => ({
      text: (el.textContent || el.value || '').trim(),
      type: el.getAttribute('type') || el.tagName.toLowerCase(),
    }))
    .filter((row) => row.text);
}

function extractForms() {
  return Array.from(document.forms)
    .slice(0, 10)
    .map((form, index) => ({
      index,
      action: form.action || '',
      method: (form.method || 'get').toLowerCase(),
      fields: Array.from(form.elements)
        .slice(0, 20)
        .map((field) => ({
          name: field.name || '',
          type: field.type || field.tagName.toLowerCase(),
        }))
        .filter((field) => field.name || field.type),
    }));
}

function inferPageType() {
  if (document.forms.length > 0) return 'form';
  if (document.querySelector('article')) return 'article';
  if (document.querySelector('[role="main"]')) return 'app';
  return 'generic';
}
