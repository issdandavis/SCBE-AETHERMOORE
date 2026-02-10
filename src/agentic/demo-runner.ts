/**
 * Minimal multi-agent orchestration runner (mock executor).
 *
 * Run with: npm run agentic:demo
 */

import { AgenticCoderPlatform } from './platform';
import { CodingTaskType } from './types';
import { logger } from '../utils/logger.js';

const demoLogger = logger.child({ module: 'agentic-demo' });

async function main(): Promise<void> {
  const platform = new AgenticCoderPlatform({
    defaultProvider: 'openai',
    requireConsensus: false,
  });

  platform.onEvent((event) => {
    const timestamp = new Date(event.timestamp).toISOString();
    demoLogger.info(`[${timestamp}] ${event.type}`, { data: event.data });
  });

  const task = platform.createTask({
    type: 'implement' as CodingTaskType,
    title: 'Demo: Implement a safe rate limiter helper',
    description:
      'Provide a small TypeScript helper function for in-memory rate limiting with a sliding window.',
    language: 'typescript',
    requirements:
      'Function should accept key, windowMs, and max; return { allowed, remaining, resetAt }.',
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
