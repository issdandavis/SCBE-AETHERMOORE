import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    // Map .js imports to .ts source files for proper test resolution
    extensions: ['.ts', '.js', '.json'],
    alias: {
      // Resolve src/*.js imports to src/*.ts for testing
    },
  },
  esbuild: {
    // Ensure proper ESM/CJS handling
    format: 'esm',
  },
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/hioujhn/**',
      '**/scbe-aethermoore/**',
      '**/scbe-aethermoore-demo/**',
    ],
    testTimeout: 30000,
    // Enterprise test suite configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/tests/**',
        '**/*.test.ts',
        '**/*.config.ts',
        '**/demo-runner.ts',
      ],
      all: true,
      // Coverage thresholds - fail if below these values
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 70,
        statements: 80,
      },
    },
    // Property-based testing configuration
    // Each property test should run minimum 100 iterations
    // Use fast-check with { numRuns: 100 } or higher
  },
});
