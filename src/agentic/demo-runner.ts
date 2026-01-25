/**
 * Minimal multi-agent orchestration runner (mock executor).
 *
 * Run with: npm run agentic:demo
 */

import { AgenticCoderPlatform } from './platform';
import { CodingTaskType } from './types';

async function main(): Promise<void> {
  const platform = new AgenticCoderPlatform({
    defaultProvider: 'openai',
    requireConsensus: false,
  });

  platform.onEvent((event) => {
    const timestamp = new Date(event.timestamp).toISOString();
    console.log(`[${timestamp}] ${event.type}`, event.data);
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

  console.log('\n=== FINAL OUTPUT ===\n');
  console.log(result.output);
  console.log('\n=== CONTRIBUTIONS ===\n');
  for (const contrib of result.contributions) {
    console.log(`${contrib.role} (${contrib.action}): confidence=${contrib.confidence.toFixed(2)}`);
  }
}

main().catch((error) => {
  console.error('Agentic demo failed:', error instanceof Error ? error.message : error);
  process.exit(1);
});
