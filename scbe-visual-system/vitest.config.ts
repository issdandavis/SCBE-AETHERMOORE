import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'node',
    include: ['__tests__/**/*.test.ts', '__tests__/**/*.test.tsx', 'tests/**/*.test.ts', 'tests/**/*.test.tsx'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['lib/**/*.ts', 'components/**/*.tsx', 'App.tsx', 'types.ts', 'src/**/*.ts'],
      exclude: ['node_modules', 'dist', 'release', 'electron'],
      thresholds: {
        lines: 70,
        branches: 60,
        functions: 70,
        statements: 70
      }
    }
  },
  resolve: {
    alias: {
      '@': '.',
      '@scbe': '../src'
    }
  }
});
