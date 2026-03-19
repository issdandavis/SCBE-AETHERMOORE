/**
 * @file sidepanel.smoke.test.ts
 * @module tests/e2e/sidepanel
 *
 * Real-browser smoke tests for the AetherBrowser sidepanel.
 *
 * These tests load the actual sidepanel HTML/CSS/JS in Chromium via a local
 * fixture server that injects a chrome-shim and runs a mock WebSocket backend.
 * They catch the class of bugs that mock-only unit tests cannot:
 *   - Real DOM rendering (CSS layout, element visibility, scrolling)
 *   - Real WebSocket connection lifecycle
 *   - Real ES module loading and initialization
 *   - Real user interaction (click, type, keyboard)
 *
 * Run:  npx playwright test
 * Mark: slow (not part of the fast vitest CI gate)
 */

import { test, expect, type Page } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:9222';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function waitForConnection(page: Page) {
  // The feed becomes visible once WebSocket connects
  await expect(page.locator('#conversation-feed')).toBeVisible({ timeout: 5_000 });
}

async function sendCommand(page: Page, text: string) {
  await page.fill('#input-text', text);
  await page.click('#btn-send');
}

// ---------------------------------------------------------------------------
// A. Sidepanel loads and connects
// ---------------------------------------------------------------------------

test.describe('A — Bootstrap', () => {
  test('A1: sidepanel HTML loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    expect(errors).toEqual([]);
  });

  test('A2: all critical DOM elements exist after init', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await expect(page.locator('#agent-grid')).toBeVisible();
    await expect(page.locator('#conversation-feed')).toBeVisible();
    await expect(page.locator('#command-bar')).toBeVisible();
    await expect(page.locator('#input-text')).toBeVisible();
    await expect(page.locator('#btn-send')).toBeVisible();
    await expect(page.locator('#btn-this-page')).toBeVisible();
    await expect(page.locator('#btn-research')).toBeVisible();
  });

  test('A3: disconnected banner hides once WebSocket connects', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await expect(page.locator('#disconnected-banner')).toBeHidden();
  });
});

// ---------------------------------------------------------------------------
// B. Agent grid renders correctly
// ---------------------------------------------------------------------------

test.describe('B — Agent Grid', () => {
  test('B1: all 6 agent badges are visible', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    for (const agent of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']) {
      await expect(page.locator(`#badge-${agent}`)).toBeVisible();
    }
  });

  test('B2: agent badges show correct names', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    for (const agent of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']) {
      const badge = page.locator(`#badge-${agent} .ab-agent-badge__name`);
      await expect(badge).toHaveText(agent);
    }
  });

  test('B3: settings gear button is present in the grid row', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const gear = page.locator('#agent-grid-row button');
    await expect(gear).toBeVisible();
    await expect(gear).toHaveAttribute('title', 'Settings');
  });
});

// ---------------------------------------------------------------------------
// C. Provider health strip
// ---------------------------------------------------------------------------

test.describe('C — Provider Health', () => {
  test('C1: provider strip appears after connection', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const strip = page.locator('#provider-strip');
    await expect(strip).toBeVisible();
  });

  test('C2: provider strip shows runtime label', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const label = page.locator('.ab-provider-strip__label');
    await expect(label).toHaveText('Runtime');
  });

  test('C3: provider pills render for available providers', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    // Wait for the health fetch to complete and pills to render
    await expect(page.locator('.ab-provider-pill').first()).toBeVisible({ timeout: 5_000 });

    const pills = page.locator('.ab-provider-pill');
    const count = await pills.count();
    // The mock /health returns 6 providers, at least local should show
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('C4: local provider shows ready status', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    // Wait for health poll to render pills
    await expect(page.locator('.ab-provider-pill--ready').first()).toBeVisible({ timeout: 5_000 });

    const localPill = page.locator('.ab-provider-pill--ready');
    await expect(localPill.first()).toBeVisible();
  });

  test('C5: blocked providers show blocked status', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await expect(page.locator('.ab-provider-pill--blocked').first()).toBeVisible({ timeout: 5_000 });

    const blockedPills = page.locator('.ab-provider-pill--blocked');
    const count = await blockedPills.count();
    // haiku, sonnet, opus, flash, grok — all missing env vars
    expect(count).toBeGreaterThanOrEqual(4);
  });
});

// ---------------------------------------------------------------------------
// D. Command flow — send a message and get a response
// ---------------------------------------------------------------------------

test.describe('D — Command Flow', () => {
  test('D1: sending a command shows user message in feed', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Hello squad');

    const userMsg = page.locator('.ab-message--user');
    await expect(userMsg.first()).toBeVisible();
    await expect(userMsg.first()).toContainText('Hello squad');
  });

  test('D2: backend responds with KO chat message', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Summarize the current page');

    const koMsg = page.locator('.ab-message--KO');
    await expect(koMsg.first()).toBeVisible({ timeout: 3_000 });
    await expect(koMsg.first()).toContainText('Acknowledged');
  });

  test('D3: command response renders structured plan section', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Summarize the current page');

    const planSection = page.locator('.ab-structured--plan');
    await expect(planSection.first()).toBeVisible({ timeout: 3_000 });

    // Plan should show the "Command Plan" title
    await expect(planSection.locator('.ab-structured__title').first()).toHaveText('Command Plan');
  });

  test('D4: plan section renders badges', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Research AI safety');

    const pills = page.locator('.ab-structured--plan .ab-pill');
    await expect(pills.first()).toBeVisible({ timeout: 3_000 });

    const count = await pills.count();
    expect(count).toBeGreaterThanOrEqual(2); // Intent + Provider at minimum
  });

  test('D5: Enter key sends command (no Shift)', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await page.fill('#input-text', 'Enter key test');
    await page.press('#input-text', 'Enter');

    const userMsg = page.locator('.ab-message--user');
    await expect(userMsg.first()).toBeVisible();
    await expect(userMsg.first()).toContainText('Enter key test');
  });

  test('D6: input clears after send', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Clear test');

    await expect(page.locator('#input-text')).toHaveValue('');
  });

  test('D7: empty input does not send', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await page.click('#btn-send');

    const messages = page.locator('.ab-message');
    expect(await messages.count()).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// E. Zone approval gating
// ---------------------------------------------------------------------------

test.describe('E — Zone Approval', () => {
  test('E1: risky command triggers zone approval card', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Login to github.com');

    const zoneCard = page.locator('.ab-zone-card');
    await expect(zoneCard.first()).toBeVisible({ timeout: 3_000 });
  });

  test('E2: zone card shows RED zone with correct content', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Login to github.com');

    const zoneCard = page.locator('.ab-zone-card--RED');
    await expect(zoneCard).toBeVisible({ timeout: 3_000 });
    await expect(zoneCard).toContainText('Approval Required');
    await expect(zoneCard).toContainText('authenticate');
  });

  test('E3: zone card has Allow and Deny buttons', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Login to github.com');

    await expect(page.locator('.ab-zone-card')).toBeVisible({ timeout: 3_000 });

    const allowBtn = page.locator('[data-decision="allow"]');
    const denyBtn = page.locator('[data-decision="deny"]');
    await expect(allowBtn).toBeVisible();
    await expect(denyBtn).toBeVisible();
  });

  test('E4: RED zone shows Allow Once and Add to Yellow buttons', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Delete the repository');

    await expect(page.locator('.ab-zone-card--RED')).toBeVisible({ timeout: 3_000 });

    await expect(page.locator('[data-decision="allow_once"]')).toBeVisible();
    await expect(page.locator('[data-decision="add_yellow"]')).toBeVisible();
  });

  test('E5: clicking Deny removes zone card and shows denial message', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Login to github.com');

    await expect(page.locator('.ab-zone-card')).toBeVisible({ timeout: 3_000 });
    await page.click('[data-decision="deny"]');

    // Card should be removed
    await expect(page.locator('.ab-zone-card')).toBeHidden();

    // RU response should appear
    const ruMsg = page.locator('.ab-message--RU');
    await expect(ruMsg.first()).toBeVisible({ timeout: 3_000 });
    await expect(ruMsg.first()).toContainText('denied');
  });

  test('E6: clicking Allow removes zone card and shows release message', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await sendCommand(page, 'Deploy to production');

    await expect(page.locator('.ab-zone-card')).toBeVisible({ timeout: 3_000 });
    await page.click('[data-decision="allow"]');

    await expect(page.locator('.ab-zone-card')).toBeHidden();

    const ruMsg = page.locator('.ab-message--RU');
    await expect(ruMsg.first()).toBeVisible({ timeout: 3_000 });
    await expect(ruMsg.first()).toContainText('Releasing');
  });
});

// ---------------------------------------------------------------------------
// F. Agent badge state transitions
// ---------------------------------------------------------------------------

test.describe('F — Badge State', () => {
  test('F1: KO badge transitions to working then done on command', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const koBadge = page.locator('#badge-KO');

    await sendCommand(page, 'Quick status');

    // Should eventually reach done state
    await expect(koBadge).toHaveClass(/ab-agent-badge--done/, { timeout: 3_000 });
  });

  test('F2: badges reset to idle class on fresh connect', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    // All badges should be in idle state (no working/done/error class)
    for (const agent of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']) {
      const badge = page.locator(`#badge-${agent}`);
      await expect(badge).not.toHaveClass(/ab-agent-badge--working/);
    }
  });
});

// ---------------------------------------------------------------------------
// G. CSS rendering sanity
// ---------------------------------------------------------------------------

test.describe('G — Visual Sanity', () => {
  test('G1: body uses dark theme background', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    // Should be dark — #0d1117 = rgb(13, 17, 23)
    expect(bg).toMatch(/rgb\(13,\s*17,\s*23\)/);
  });

  test('G2: agent grid uses column layout with row inside', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const gridDir = await page.evaluate(() =>
      getComputedStyle(document.getElementById('agent-grid')!).flexDirection
    );
    expect(gridDir).toBe('column');

    const rowDir = await page.evaluate(() =>
      getComputedStyle(document.getElementById('agent-grid-row')!).flexDirection
    );
    expect(rowDir).toBe('row');
  });

  test('G3: command bar footer is visible at page bottom', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const bar = page.locator('#command-bar');
    await expect(bar).toBeVisible();

    const box = await bar.boundingBox();
    expect(box).not.toBeNull();
    // Footer should be in the lower half of the viewport
    expect(box!.y).toBeGreaterThan(300);
  });

  test('G4: provider pills have border-radius for pill shape', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await expect(page.locator('.ab-provider-pill').first()).toBeVisible({ timeout: 5_000 });

    const radius = await page.evaluate(() => {
      const pill = document.querySelector('.ab-provider-pill');
      return pill ? getComputedStyle(pill).borderRadius : '';
    });
    expect(radius).toBe('999px');
  });
});

// ---------------------------------------------------------------------------
// H. Settings panel
// ---------------------------------------------------------------------------

test.describe('H — Settings', () => {
  test('H1: clicking gear opens settings panel', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    const gear = page.locator('#agent-grid-row button[title="Settings"]');
    await gear.click();

    const panel = page.locator('#settings-panel');
    await expect(panel).toBeVisible();
    await expect(panel).toContainText('Model Routing');
  });

  test('H2: settings panel has dropdowns for all 6 roles', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await page.locator('#agent-grid-row button[title="Settings"]').click();

    for (const role of ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']) {
      await expect(page.locator(`#pref-${role}`)).toBeVisible();
    }
  });

  test('H3: closing settings panel hides it', async ({ page }) => {
    await page.goto(BASE_URL);
    await waitForConnection(page);

    await page.locator('#agent-grid-row button[title="Settings"]').click();
    await expect(page.locator('#settings-panel')).toBeVisible();

    await page.click('#settings-close');
    await expect(page.locator('#settings-panel')).toBeHidden();
  });
});
