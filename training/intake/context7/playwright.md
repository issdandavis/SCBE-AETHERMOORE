# Playwright

Playwright is a framework for web testing and automation. Enables cross-browser testing of Chromium, Firefox, and WebKit with a single API. Features auto-wait, web-first assertions, and full test isolation.

## Basic Test with Page Fixture

The page fixture provides an isolated browser page for each test, automatically set up and torn down.

```javascript
import { test, expect } from '@playwright/test';

test('basic test', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await expect(page).toHaveTitle(/Playwright/);
});
```

## Navigation and Assertions

Navigate to pages, validate titles, locate elements by role, and verify attributes.

```javascript
import { test, expect } from '@playwright/test';

test('get started link', async ({ page }) => {
  await page.goto('https://playwright.dev');
  await expect(page).toHaveTitle(/Playwright/);

  const getStarted = page.getByRole('link', { name: 'Get started' });
  await expect(getStarted).toHaveAttribute('href', '/docs/intro');
  await getStarted.click();

  await expect(page.getByRole('heading', { name: 'Installation' })).toBeVisible();
});
```

## Locators and Auto-Wait

Locators support auto-waiting for actionability and can be reused for multiple operations.

```javascript
const getStarted = page.locator('text=Get Started');
await expect(getStarted).toHaveAttribute('href', '/docs/intro');
await getStarted.click();
```
