"use strict";
/**
 * Minimal multi-agent orchestration runner (mock executor).
 *
 * Run with: npm run agentic:demo
 */
Object.defineProperty(exports, "__esModule", { value: true });
const platform_1 = require("./platform");
const logger_js_1 = require("../utils/logger.js");
const demoLogger = logger_js_1.logger.child({ module: 'agentic-demo' });
async function main() {
    const platform = new platform_1.AgenticCoderPlatform({
        defaultProvider: 'openai',
        requireConsensus: false,
    });
    platform.onEvent((event) => {
        const timestamp = new Date(event.timestamp).toISOString();
        demoLogger.info(`[${timestamp}] ${event.type}`, { data: event.data });
    });
    const task = platform.createTask({
        type: 'implement',
        title: 'Demo: Implement a safe rate limiter helper',
        description: 'Provide a small TypeScript helper function for in-memory rate limiting with a sliding window.',
        language: 'typescript',
        requirements: 'Function should accept key, windowMs, and max; return { allowed, remaining, resetAt }.',
        constraints: ['No external dependencies', 'Keep it concise'],
    });
    const result = await platform.executeTask(task.id);
    demoLogger.info('=== FINAL OUTPUT ===');
    demoLogger.info(result.output);
    demoLogger.info('=== CONTRIBUTIONS ===');
    for (const contrib of result.contributions) {
        demoLogger.info(`${contrib.role} (${contrib.action})`, { confidence: contrib.confidence });
    }
}
main().catch((error) => {
    demoLogger.error('Agentic demo failed', {
        error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
});
//# sourceMappingURL=demo-runner.js.map