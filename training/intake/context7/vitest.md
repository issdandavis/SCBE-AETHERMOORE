# Vitest
> Source: Context7 MCP | Category: code
> Fetched: 2026-04-04

### Mocking Overview

Source: https://github.com/vitest-dev/vitest/blob/main/docs/guide/mocking.md

When writing tests it's only a matter of time before you need to create a "fake" version of an internal or external service. This is commonly referred to as **mocking**. Vitest provides utility functions to help you out through its `vi` helper. You can import it from `vitest` or access it globally if global configuration is enabled. Always remember to clear or restore mocks before or after each test run to undo mock state changes between runs.

---

### Configuring Vitest with `vitest.config.ts`

Source: https://context7.com/vitest-dev/vitest/llms.txt

This configuration file demonstrates common settings for Vitest including globals, environment, setup files, include/exclude patterns, code coverage, timeouts, reporters, parallelization, mocking behavior, and snapshot formatting.

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    // Globals (describe, test, expect without imports)
    globals: true,

    // Environment
    environment: 'jsdom', // or 'happy-dom', 'node'

    // Setup files
    setupFiles: ['./test/setup.ts'],

    // Include/exclude patterns
    include: ['**/*.{test,spec}.{js,ts,jsx,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**'],

    // Coverage
    coverage: {
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.test.ts']
    },

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,

    // Reporters
    reporters: ['default', 'json'],

    // Parallelization
    pool: 'threads', // or 'forks', 'vmThreads'
    poolOptions: {
      threads: {
        singleThread: false
      }
    },

    // Mocking
    clearMocks: true,
    restoreMocks: true,

    // Snapshots
    snapshotFormat: {
      printBasicPrototype: false
    }
  }
})
```

---

### Configure mockReset in Vitest Config

Source: https://github.com/vitest-dev/vitest/blob/main/docs/config/mockreset.md

Enable automatic mock reset in Vitest configuration. When set to true, `vi.resetAllMocks()` is called before each test, clearing mock history and resetting implementations. Note: This may cause issues with concurrent async tests as mock state is shared across tests in progress.

```javascript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    mockReset: true,
  },
})
```

---

### Configure restoreMocks in Vitest Config

Source: https://github.com/vitest-dev/vitest/blob/main/docs/config/restoremocks.md

Enable automatic mock restoration before each test by setting restoreMocks to true. This calls `vi.restoreAllMocks()` automatically and restores all original implementations on spies created with `vi.spyOn`.

```javascript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    restoreMocks: true,
  },
})
```

---

### Configure clearMocks in Vitest Config

Source: https://github.com/vitest-dev/vitest/blob/main/docs/config/clearmocks.md

Enable the clearMocks option to automatically clear mock history before each test.

```javascript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    clearMocks: true,
  },
})
```
