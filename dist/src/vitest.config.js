"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const config_1 = require("vitest/config");
exports.default = (0, config_1.defineConfig)({
    test: {
        globals: true,
        environment: 'node',
        include: ['../tests/**/*.test.ts'],
        exclude: [
            '**/node_modules/**',
            '**/dist/**',
            '**/hioujhn/**',
            '**/scbe-aethermoore/**',
            '**/scbe-aethermoore-demo/**',
        ],
        testTimeout: 10000,
    },
});
//# sourceMappingURL=vitest.config.js.map