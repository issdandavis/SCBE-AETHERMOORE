import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // These tests exercise process launchers and filesystem queues. Running
    // every file concurrently on Windows starves child processes and creates
    // false five-second timeouts, so keep file scheduling deterministic.
    fileParallelism: false,
  },
});
