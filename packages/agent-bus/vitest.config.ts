import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // Queue tests launch governed subprocesses. Serial files and a realistic
    // Windows timeout prevent CPU contention from being mistaken for failure.
    fileParallelism: false,
    testTimeout: 20_000,
  },
});
