import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*.smoke.test.ts',
  timeout: 30_000,
  retries: 0,
  workers: 1,
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 400, height: 700 },
  },
  webServer: {
    command: 'node tests/e2e/fixtures/serve-sidepanel.mjs',
    port: 9222,
    reuseExistingServer: true,
    timeout: 10_000,
  },
});
