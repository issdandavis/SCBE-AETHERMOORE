/**
 * @file socialContent.ts
 * @module skills/socialContent
 * @layer L13 (Content Decision)
 * @component Post-to-X Notion Skill
 * @version 1.0.0
 *
 * Transforms marketing content from Notion (or any source) into
 * tweet-ready social media posts. Handles character limits,
 * hashtag generation, and brand voice consistency.
 */
export interface MarketingContent {
    /** Main headline or campaign name */
    headline?: string;
    /** Product or service description */
    description?: string;
    /** Key selling points */
    sellingPoints?: string[];
    /** Current promotions or offers */
    promotions?: string[];
    /** Brand slogans or taglines */
    slogans?: string[];
    /** Target keywords for hashtags */
    keywords?: string[];
    /** Call to action */
    cta?: string;
    /** Link to include (will be shortened assumption) */
    link?: string;
}
export interface TweetOptions {
    /** Maximum character count (default 280) */
    maxChars?: number;
    /** Include hashtags (default true) */
    includeHashtags?: boolean;
    /** Maximum hashtags to include (default 3) */
    maxHashtags?: number;
    /** Tone: casual, professional, urgent, playful */
    tone?: 'casual' | 'professional' | 'urgent' | 'playful';
    /** Include emoji (default false for professional) */
    includeEmoji?: boolean;
}
export interface GeneratedTweet {
    /** The tweet text ready to post */
    text: string;
    /** Character count */
    charCount: number;
    /** Characters remaining */
    charsRemaining: number;
    /** Hashtags used */
    hashtags: string[];
    /** Style variation name */
    style: string;
}
/**
 * Generates hashtags from keywords and content
 */
export declare function generateHashtags(content: MarketingContent, max?: number): string[];
/**
 * Truncates text to fit character limit while keeping it readable
 */
export declare function smartTruncate(text: string, maxLength: number): string;
/**
 * Main function: Generate multiple tweet variations from marketing content
 *
 * @example
 * ```typescript
 * const content = {
 *   headline: 'AI Security That Actually Works',
 *   description: 'Post-quantum encryption for the modern era',
 *   sellingPoints: ['Military-grade encryption', 'Easy setup', 'Free tier available'],
 *   promotions: ['50% off first month with code LAUNCH50'],
 *   keywords: ['AI', 'Security', 'Crypto'],
 *   cta: 'Try it free',
 *   link: 'https://example.com'
 * };
 *
 * const tweets = generateTweets(content, { tone: 'professional' });
 * tweets.forEach(t => console.log(t.text));
 * ```
 */
export declare function generateTweets(content: MarketingContent, options?: TweetOptions): GeneratedTweet[];
/**
 * Quick helper: Generate a single best tweet from content
 */
export declare function generateBestTweet(content: MarketingContent, options?: TweetOptions): GeneratedTweet | null;
/**
 * Parse simple text content into MarketingContent structure
 * Useful for quick conversion of Notion page text
 */
export declare function parseNotionContent(text: string): MarketingContent;
declare const _default: {
    generateTweets: typeof generateTweets;
    generateBestTweet: typeof generateBestTweet;
    generateHashtags: typeof generateHashtags;
    parseNotionContent: typeof parseNotionContent;
    smartTruncate: typeof smartTruncate;
};
export default _default;
//# sourceMappingURL=socialContent.d.ts.map