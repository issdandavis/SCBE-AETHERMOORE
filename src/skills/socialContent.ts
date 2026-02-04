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

// Common marketing power words by tone
const POWER_WORDS: Record<string, string[]> = {
  casual: ['check out', 'loving', 'game-changer', 'finally', 'so good'],
  professional: ['introducing', 'discover', 'transform', 'elevate', 'unlock'],
  urgent: ['limited time', "don't miss", 'act now', 'last chance', 'ending soon'],
  playful: ['guess what', 'plot twist', 'spoiler alert', 'hot take', 'big mood'],
};

const EMOJI_MAP: Record<string, string> = {
  casual: '',
  professional: '',
  urgent: '',
  playful: '',
};

/**
 * Generates hashtags from keywords and content
 */
export function generateHashtags(content: MarketingContent, max: number = 3): string[] {
  const hashtags: string[] = [];

  // Use provided keywords first
  if (content.keywords) {
    for (const kw of content.keywords) {
      const tag = '#' + kw.replace(/\s+/g, '').replace(/[^a-zA-Z0-9]/g, '');
      if (tag.length > 1 && !hashtags.includes(tag)) {
        hashtags.push(tag);
      }
      if (hashtags.length >= max) break;
    }
  }

  // Extract from headline if needed
  if (hashtags.length < max && content.headline) {
    const words = content.headline.split(/\s+/).filter((w) => w.length > 4);
    for (const word of words) {
      const tag = '#' + word.replace(/[^a-zA-Z0-9]/g, '');
      if (tag.length > 3 && !hashtags.includes(tag)) {
        hashtags.push(tag);
      }
      if (hashtags.length >= max) break;
    }
  }

  return hashtags;
}

/**
 * Truncates text to fit character limit while keeping it readable
 */
export function smartTruncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;

  // Try to cut at sentence boundary
  const truncated = text.slice(0, maxLength - 3);
  const lastPeriod = truncated.lastIndexOf('.');
  const lastSpace = truncated.lastIndexOf(' ');

  if (lastPeriod > maxLength * 0.6) {
    return truncated.slice(0, lastPeriod + 1);
  }

  if (lastSpace > 0) {
    return truncated.slice(0, lastSpace) + '...';
  }

  return truncated + '...';
}

/**
 * Creates a tweet focused on the headline/hook
 */
function createHeadlineTweet(
  content: MarketingContent,
  options: TweetOptions
): GeneratedTweet | null {
  if (!content.headline) return null;

  const hashtags = options.includeHashtags ? generateHashtags(content, options.maxHashtags) : [];
  const hashtagStr = hashtags.join(' ');

  let tweet = content.headline;

  // Add CTA if fits
  if (content.cta) {
    tweet += ` ${content.cta}`;
  }

  // Add link if provided
  if (content.link) {
    tweet += ` ${content.link}`;
  }

  // Calculate space for hashtags
  const maxContent = (options.maxChars || 280) - (hashtagStr ? hashtagStr.length + 2 : 0);
  tweet = smartTruncate(tweet, maxContent);

  // Add hashtags
  if (hashtagStr) {
    tweet += '\n\n' + hashtagStr;
  }

  return {
    text: tweet,
    charCount: tweet.length,
    charsRemaining: (options.maxChars || 280) - tweet.length,
    hashtags,
    style: 'headline',
  };
}

/**
 * Creates a tweet focused on a selling point
 */
function createSellingPointTweet(
  content: MarketingContent,
  options: TweetOptions
): GeneratedTweet | null {
  if (!content.sellingPoints || content.sellingPoints.length === 0) return null;

  const hashtags = options.includeHashtags ? generateHashtags(content, options.maxHashtags) : [];
  const hashtagStr = hashtags.join(' ');
  const tone = options.tone || 'professional';

  // Pick a power word for the tone
  const powerWords = POWER_WORDS[tone];
  const powerWord = powerWords[Math.floor(Math.random() * powerWords.length)];

  // Use first selling point
  let tweet = `${powerWord.charAt(0).toUpperCase() + powerWord.slice(1)}: ${content.sellingPoints[0]}`;

  if (content.link) {
    tweet += ` ${content.link}`;
  }

  const maxContent = (options.maxChars || 280) - (hashtagStr ? hashtagStr.length + 2 : 0);
  tweet = smartTruncate(tweet, maxContent);

  if (hashtagStr) {
    tweet += '\n\n' + hashtagStr;
  }

  return {
    text: tweet,
    charCount: tweet.length,
    charsRemaining: (options.maxChars || 280) - tweet.length,
    hashtags,
    style: 'selling-point',
  };
}

/**
 * Creates a tweet focused on a promotion/offer
 */
function createPromoTweet(content: MarketingContent, options: TweetOptions): GeneratedTweet | null {
  if (!content.promotions || content.promotions.length === 0) return null;

  const hashtags = options.includeHashtags ? generateHashtags(content, options.maxHashtags) : [];
  const hashtagStr = hashtags.join(' ');

  let tweet = content.promotions[0];

  if (content.cta) {
    tweet += ` ${content.cta}`;
  }

  if (content.link) {
    tweet += ` ${content.link}`;
  }

  const maxContent = (options.maxChars || 280) - (hashtagStr ? hashtagStr.length + 2 : 0);
  tweet = smartTruncate(tweet, maxContent);

  if (hashtagStr) {
    tweet += '\n\n' + hashtagStr;
  }

  return {
    text: tweet,
    charCount: tweet.length,
    charsRemaining: (options.maxChars || 280) - tweet.length,
    hashtags,
    style: 'promotion',
  };
}

/**
 * Creates a tweet using a slogan/tagline
 */
function createSloganTweet(
  content: MarketingContent,
  options: TweetOptions
): GeneratedTweet | null {
  if (!content.slogans || content.slogans.length === 0) return null;

  const hashtags = options.includeHashtags ? generateHashtags(content, options.maxHashtags) : [];
  const hashtagStr = hashtags.join(' ');

  let tweet = content.slogans[0];

  if (content.headline && content.headline !== content.slogans[0]) {
    tweet = `${content.headline}\n\n${content.slogans[0]}`;
  }

  if (content.link) {
    tweet += ` ${content.link}`;
  }

  const maxContent = (options.maxChars || 280) - (hashtagStr ? hashtagStr.length + 2 : 0);
  tweet = smartTruncate(tweet, maxContent);

  if (hashtagStr) {
    tweet += '\n\n' + hashtagStr;
  }

  return {
    text: tweet,
    charCount: tweet.length,
    charsRemaining: (options.maxChars || 280) - tweet.length,
    hashtags,
    style: 'slogan',
  };
}

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
export function generateTweets(
  content: MarketingContent,
  options: TweetOptions = {}
): GeneratedTweet[] {
  const opts: TweetOptions = {
    maxChars: 280,
    includeHashtags: true,
    maxHashtags: 3,
    tone: 'professional',
    includeEmoji: false,
    ...options,
  };

  const tweets: GeneratedTweet[] = [];

  // Generate different styles
  const headline = createHeadlineTweet(content, opts);
  if (headline) tweets.push(headline);

  const sellingPoint = createSellingPointTweet(content, opts);
  if (sellingPoint) tweets.push(sellingPoint);

  const promo = createPromoTweet(content, opts);
  if (promo) tweets.push(promo);

  const slogan = createSloganTweet(content, opts);
  if (slogan) tweets.push(slogan);

  // If no content generated, create a simple one from description
  if (tweets.length === 0 && content.description) {
    const hashtags = opts.includeHashtags ? generateHashtags(content, opts.maxHashtags) : [];
    const hashtagStr = hashtags.join(' ');
    const maxContent = (opts.maxChars || 280) - (hashtagStr ? hashtagStr.length + 2 : 0);
    let text = smartTruncate(content.description, maxContent);
    if (hashtagStr) text += '\n\n' + hashtagStr;

    tweets.push({
      text,
      charCount: text.length,
      charsRemaining: (opts.maxChars || 280) - text.length,
      hashtags,
      style: 'description',
    });
  }

  return tweets;
}

/**
 * Quick helper: Generate a single best tweet from content
 */
export function generateBestTweet(
  content: MarketingContent,
  options: TweetOptions = {}
): GeneratedTweet | null {
  const tweets = generateTweets(content, options);
  if (tweets.length === 0) return null;

  // Prefer headline, then promo, then others
  const headline = tweets.find((t) => t.style === 'headline');
  if (headline) return headline;

  const promo = tweets.find((t) => t.style === 'promotion');
  if (promo) return promo;

  return tweets[0];
}

/**
 * Parse simple text content into MarketingContent structure
 * Useful for quick conversion of Notion page text
 */
export function parseNotionContent(text: string): MarketingContent {
  const lines = text.split('\n').filter((l) => l.trim());
  const content: MarketingContent = {};

  // First non-empty line is usually the headline
  if (lines.length > 0) {
    content.headline = lines[0].trim();
  }

  // Look for common patterns
  const sellingPoints: string[] = [];
  const promotions: string[] = [];
  const keywords: string[] = [];

  for (const line of lines.slice(1)) {
    const trimmed = line.trim();

    // Lines starting with # are hashtags/keywords
    if (trimmed.startsWith('#') && !trimmed.includes(' ')) {
      keywords.push(trimmed.replace(/^#+/, '').trim());
      continue;
    }

    // Bullet points (-, *, •, ✓) are selling points
    if (/^[-*•✓]\s/.test(trimmed)) {
      sellingPoints.push(trimmed.replace(/^[-*•✓]\s*/, ''));
      continue;
    }

    // Lines with % or $ or promotion keywords are promotions
    if (/%\s*off|discount|\$\d|free\s|sale\b|limited\s*time|code\s+\w+/i.test(trimmed)) {
      promotions.push(trimmed);
      continue;
    }

    // Short catchy lines might be slogans
    if (trimmed.length < 50 && trimmed.length > 5 && !content.slogans) {
      content.slogans = [trimmed];
      continue;
    }

    // Longer lines are description
    if (!content.description && trimmed.length >= 50) {
      content.description = trimmed;
    }
  }

  if (sellingPoints.length > 0) content.sellingPoints = sellingPoints;
  if (promotions.length > 0) content.promotions = promotions;
  if (keywords.length > 0) content.keywords = keywords;

  // Extract URLs
  const urlMatch = text.match(/https?:\/\/[^\s]+/);
  if (urlMatch) {
    content.link = urlMatch[0];
  }

  return content;
}

// Export default for easy importing
export default {
  generateTweets,
  generateBestTweet,
  generateHashtags,
  parseNotionContent,
  smartTruncate,
};
