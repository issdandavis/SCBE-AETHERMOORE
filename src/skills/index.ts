/**
 * @file index.ts
 * @module skills
 * @layer L13 (Decision Layer)
 * @component Skills Module
 * @version 1.0.0
 *
 * Skills are reusable capabilities for automating common tasks.
 * Each skill transforms inputs into actionable outputs.
 */

export * from './socialContent';
export { default as socialContent } from './socialContent';

// Re-export commonly used functions at top level
export {
  generateTweets,
  generateBestTweet,
  generateHashtags,
  parseNotionContent,
  smartTruncate,
} from './socialContent';

export type {
  MarketingContent,
  TweetOptions,
  GeneratedTweet,
} from './socialContent';
