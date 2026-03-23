/**
 * SCBE AI Bridge — Google Colab Bridge
 *
 * Provides clean API for interacting with Colab notebooks:
 * - Read/write cell content
 * - Run cells
 * - Read outputs
 * - Interact with Gemini AI chat
 * - Scroll to specific cells
 * - Get notebook state
 *
 * Exposes window.__scbe_colab for Playwright to call directly.
 */

(function () {
  'use strict';

  const BRIDGE_NAME = 'colab';

  // Wait for Colab to fully load
  function waitForColab(maxWait = 15000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = () => {
        // Colab is ready when we can find notebook cells
        const cells = document.querySelectorAll('.cell');
        if (cells.length > 0) {
          resolve(cells.length);
          return;
        }
        if (Date.now() - start > maxWait) {
          reject(new Error('Colab did not load in time'));
          return;
        }
        setTimeout(check, 500);
      };
      check();
    });
  }

  // Get all cells with their content and type
  function getCells() {
    const cells = document.querySelectorAll('.cell');
    return Array.from(cells).map((cell, i) => {
      const isCode = cell.classList.contains('code') || cell.querySelector('.monaco-editor');
      const isMarkdown = cell.classList.contains('text') || cell.querySelector('.markup');

      // Get code content from Monaco editor
      let content = '';
      if (isCode) {
        const lines = cell.querySelectorAll('.view-line');
        content = Array.from(lines).map(l => l.textContent).join('\n');
      } else {
        const rendered = cell.querySelector('.markup, .text-cell-render');
        content = rendered ? rendered.textContent : '';
      }

      // Get output
      const outputEl = cell.querySelector('.output, .output_area');
      const output = outputEl ? outputEl.textContent : '';

      return {
        index: i,
        type: isCode ? 'code' : 'markdown',
        content: content.trim(),
        output: output.trim().slice(0, 2000), // cap output length
        hasOutput: output.trim().length > 0,
      };
    });
  }

  // Get cell count
  function getCellCount() {
    return document.querySelectorAll('.cell').length;
  }

  // Scroll to a specific cell
  function scrollToCell(index) {
    const cells = document.querySelectorAll('.cell');
    if (index >= 0 && index < cells.length) {
      cells[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
      return true;
    }
    return false;
  }

  // Click the "+ Code" button to add a new code cell
  function addCodeCell() {
    const btn = document.querySelector('#toolbar-add-code');
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }

  // Click the "+ Text" button to add a markdown cell
  function addTextCell() {
    const btn = document.querySelector('#toolbar-add-text');
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }

  // Set content of the currently focused/last cell using Monaco editor's model
  function setCellContent(code) {
    // Find the focused cell's Monaco editor
    const focusedCell = document.querySelector('.cell.focused, .cell.selected, .cell:last-child');
    if (!focusedCell) return { ok: false, error: 'No focused cell' };

    const editor = focusedCell.querySelector('.monaco-editor');
    if (!editor) return { ok: false, error: 'No Monaco editor in cell' };

    // Access Monaco's internal model via the editor's viewModel
    const editorId = editor.getAttribute('data-uri') || editor.getAttribute('data-keybinding-context');

    // Use execCommand to paste content (works with Monaco)
    const textarea = focusedCell.querySelector('textarea.inputarea');
    if (textarea) {
      textarea.focus();
      textarea.value = code;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));

      // Also try the clipboard approach
      const dt = new DataTransfer();
      dt.setData('text/plain', code);
      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: dt,
        bubbles: true,
        cancelable: true,
      });
      textarea.dispatchEvent(pasteEvent);

      return { ok: true, method: 'paste' };
    }

    return { ok: false, error: 'No textarea found' };
  }

  // Set cell content using Colab's internal notebook API (more reliable)
  function setCellContentV2(code, cellIndex) {
    try {
      // Colab exposes colab.global.notebook internally
      const nb = window.colab?.global?.notebook;
      if (nb && nb.cells) {
        const idx = cellIndex ?? nb.cells.length - 1;
        const cell = nb.cells[idx];
        if (cell && cell.setText) {
          cell.setText(code);
          return { ok: true, method: 'colab-api', index: idx };
        }
      }
    } catch (e) {
      // Fall through to DOM approach
    }

    // Fallback: use DOM manipulation
    return setCellContent(code);
  }

  // Run the currently focused cell
  function runCell() {
    // Ctrl+Enter runs the current cell in Colab
    const event = new KeyboardEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      ctrlKey: true,
      bubbles: true,
    });
    document.activeElement.dispatchEvent(event);
    return true;
  }

  // Run a specific cell by index
  function runCellByIndex(index) {
    const cells = document.querySelectorAll('.cell');
    if (index >= 0 && index < cells.length) {
      const cell = cells[index];
      const runBtn = cell.querySelector('[aria-label="Run cell"], .cell-execution-indicator, button.run-button');
      if (runBtn) {
        runBtn.click();
        return { ok: true, method: 'button' };
      }
      // Try clicking into the cell first then Ctrl+Enter
      cell.click();
      setTimeout(() => {
        document.dispatchEvent(new KeyboardEvent('keydown', {
          key: 'Enter', code: 'Enter', ctrlKey: true, bubbles: true,
        }));
      }, 200);
      return { ok: true, method: 'keyboard' };
    }
    return { ok: false, error: 'Invalid cell index' };
  }

  // Open Gemini AI chat
  function openGeminiChat() {
    // Look for the Gemini button (blue sparkle FAB)
    const selectors = [
      '[data-testid="colab-ai-button"]',
      'button[aria-label*="Gemini"]',
      'button[aria-label*="AI"]',
      '.colab-gemini-button',
      '#gemini-fab',
    ];
    for (const sel of selectors) {
      const btn = document.querySelector(sel);
      if (btn) {
        btn.click();
        return { ok: true, selector: sel };
      }
    }
    // Try finding by SVG content or position (bottom center blue button)
    const allBtns = document.querySelectorAll('button');
    for (const btn of allBtns) {
      const rect = btn.getBoundingClientRect();
      // Gemini button is usually bottom-center, blue, circular
      if (rect.bottom > window.innerHeight - 100 &&
          rect.left > window.innerWidth / 2 - 100 &&
          rect.right < window.innerWidth / 2 + 100) {
        btn.click();
        return { ok: true, method: 'position-guess' };
      }
    }
    return { ok: false, error: 'Gemini button not found' };
  }

  // Type into Gemini chat
  function typeInGeminiChat(text) {
    const chatInput = document.querySelector(
      '[aria-label*="Gemini"] textarea, ' +
      '[aria-label*="AI"] textarea, ' +
      '.gemini-input textarea, ' +
      '[data-testid="gemini-input"] textarea'
    );
    if (chatInput) {
      chatInput.focus();
      chatInput.value = text;
      chatInput.dispatchEvent(new Event('input', { bubbles: true }));
      return { ok: true };
    }
    return { ok: false, error: 'Gemini chat input not found' };
  }

  // Submit Gemini chat (press Enter)
  function submitGeminiChat() {
    const chatInput = document.querySelector(
      '[aria-label*="Gemini"] textarea, ' +
      '.gemini-input textarea'
    );
    if (chatInput) {
      chatInput.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', bubbles: true,
      }));
      return { ok: true };
    }
    return { ok: false, error: 'Gemini chat input not found' };
  }

  // Get runtime status
  function getRuntimeStatus() {
    const ramEl = document.querySelector('[data-testid="ram-display"], .ram-indicator');
    const diskEl = document.querySelector('[data-testid="disk-display"], .disk-indicator');
    const gpuEl = document.querySelector('[data-testid="gpu-display"]');
    const connected = document.querySelector('.colab-connected-indicator, [aria-label="Connected"]');

    return {
      connected: !!connected || document.title.includes('- Colab'),
      ram: ramEl?.textContent || 'unknown',
      disk: diskEl?.textContent || 'unknown',
      gpu: gpuEl?.textContent || 'unknown',
    };
  }

  // Get notebook title
  function getNotebookTitle() {
    const titleEl = document.querySelector('.notebook-name, [data-testid="notebook-name"]');
    return titleEl?.textContent || document.title.replace(' - Colab', '');
  }

  // --- Expose the API globally for Playwright ---
  const api = {
    getCells,
    getCellCount,
    scrollToCell,
    addCodeCell,
    addTextCell,
    setCellContent,
    setCellContentV2,
    runCell,
    runCellByIndex,
    openGeminiChat,
    typeInGeminiChat,
    submitGeminiChat,
    getRuntimeStatus,
    getNotebookTitle,
  };

  window.__scbe_colab = api;

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

  // Announce bridge ready
  waitForColab().then((cellCount) => {
    console.log(`[SCBE Colab Bridge] Ready. ${cellCount} cells found.`);
    chrome.runtime.sendMessage({ type: 'bridge-ready', bridge: BRIDGE_NAME, cellCount });
  }).catch((e) => {
    console.warn(`[SCBE Colab Bridge] ${e.message}`);
  });

})();
