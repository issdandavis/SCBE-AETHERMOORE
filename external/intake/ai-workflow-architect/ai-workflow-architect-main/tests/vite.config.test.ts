import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import path from 'path';

// Mock process.env
const originalEnv = process.env;

describe('vite.config.ts', () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should return default configuration in production', async () => {
    process.env.NODE_ENV = 'production';
    delete process.env.REPL_ID;

    // Import the config
    // We use a query parameter to force reload the module to ensure env vars are picked up if they are read at top level (though here they are read inside the function)
    const viteConfigModule = await import('../vite.config?update=' + Date.now());
    const viteConfigFn = viteConfigModule.default;

    // It should be a function
    expect(typeof viteConfigFn).toBe('function');

    // Call the function to get the config object
    // The function in vite.config.ts is defined as async () => ... (no arguments)
    // So we call it with no arguments.
    // Casting to any to avoid strict type checks if the definition changes.
    const config = await (viteConfigFn as any)();

    // Check resolve aliases
    expect(config.resolve).toBeDefined();
    expect(config.resolve?.alias).toBeDefined();
    // @ts-ignore
    expect(config.resolve?.alias?.['@']).toBeDefined();
    // @ts-ignore
    expect(config.resolve?.alias?.['@shared']).toBeDefined();
    // @ts-ignore
    expect(config.resolve?.alias?.['@assets']).toBeDefined();

    // Check root and build
    expect(config.root).toContain('client');
    expect(config.build?.outDir).toContain('dist/public');
    expect(config.build?.emptyOutDir).toBe(true);

    // Check server
    expect(config.server?.host).toBe('0.0.0.0');
    expect(config.server?.allowedHosts).toBe(true);

    // Check plugins count (react, runtimeErrorOverlay, tailwindcss, metaImagesPlugin)
    // cartographer and devBanner should be undefined/absent
    expect(config.plugins).toBeDefined();
    // We expect at least the 4 base plugins
    expect(config.plugins?.length).toBeGreaterThanOrEqual(4);
  });

  it('should include replit plugins when in dev environment and REPL_ID is set', async () => {
    process.env.NODE_ENV = 'development';
    process.env.REPL_ID = 'test-repl-id';

    const viteConfigModule = await import('../vite.config?update=' + Date.now());
    const viteConfigFn = viteConfigModule.default;

    const config = await (viteConfigFn as any)();

    expect(config.plugins).toBeDefined();
    // Should have more plugins than the production one
    // Base 4 + cartographer + devBanner = 6
    expect(config.plugins?.length).toBeGreaterThanOrEqual(6);
  });
});
