# Browser + Playwright Notes

## Use Cases

- Collect evidence pages or metadata not exposed by MCP connectors.
- Capture screenshots or HTML snapshots for audit pages.
- Verify UI-level artifact changes for Hugging Face cards, PR comments, or dashboards.

## Browser Capability Rules

1. Keep actions deterministic:
   - fixed viewport
   - deterministic selectors
   - stable timeouts
2. Never paste secrets into scripts.
3. Prefer service API calls over scraping when API exists.
4. Treat each browser interaction as a tool action with explicit timeout and retry.

## Recommended Flow

1. Start intent extraction from user request.
2. Generate browse target list with explicit URL and expected artifact.
3. Run Playwright task in isolated profile/session.
4. Extract:
   - rendered title
   - relevant status text
   - optional screenshot path
5. Write extraction result into:
   - repository evidence log
   - Notion status row
   - or chain payload for next tool step

## Minimal Playwright Skeleton

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    text = page.inner_text("body")
    browser.close()
```

## Failsafe Behavior

- If browsing blocks, retry once with lower fidelity wait.
- If still blocked, route to API discovery and continue the chain with a clear failure reason.
