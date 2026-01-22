import { defineConfig } from 'vitest/config';

export default defineConfig({
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
      provider: 'c8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/tests/**',
        '**/*.test.ts',
        '**/*.config.ts',
      ],
      all: true,
      lines: 80,
      functions: 80,
      branches: 70,
      statements: 80,
    },
    // Property-based testing configuration
    // Each property test should run minimum 100 iterations
    // Use fast-check with { numRuns: 100 } or higher
  },
});
