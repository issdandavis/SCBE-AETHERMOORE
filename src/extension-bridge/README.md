# SCBE AI Bridge Extension

Chrome extension that acts as a diplomat between Claude Code (Playwright/CDP) and complex web apps.

## Install

1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select this directory: `src/extension-bridge/`

## How It Works

Once installed, every page gets `window.__scbe` with universal tools. Specific sites get specialized bridges:

| Site | Global | Commands |
|------|--------|----------|
| All pages | `window.__scbe` | getPageText, clickByText, fillByLabel, getFormFields, snapshot |
| Colab | `window.__scbe_colab` | getCells, setCellContentV2, runCellByIndex, addCodeCell, openGeminiChat, typeInGeminiChat |
| Cash App | `window.__scbe_cashapp` | getBalance, getTransactions, navigateToTaxes |

## Usage from Playwright

```python
# Instead of fighting the DOM:
page.evaluate("window.__scbe_colab.addCodeCell()")
page.evaluate("window.__scbe_colab.setCellContentV2('print(hello)', -1)")
page.evaluate("window.__scbe_colab.runCell()")

# Read all cells
cells = page.evaluate("window.__scbe_colab.getCells()")

# Interact with Gemini
page.evaluate("window.__scbe_colab.openGeminiChat()")
page.evaluate("window.__scbe_colab.typeInGeminiChat('Run PhaseTunnelGate on Mistral-7B')")
page.evaluate("window.__scbe_colab.submitGeminiChat()")

# Cash App
balance = page.evaluate("window.__scbe_cashapp.getBalance()")

# Universal
page.evaluate("window.__scbe.clickByText('Submit')")
page.evaluate("window.__scbe.fillByLabel('Email', 'test@test.com')")
```

## Adding New Bridges

1. Create `bridges/newsite.js`
2. Add to `manifest.json` content_scripts
3. Expose as `window.__scbe_newsite`
