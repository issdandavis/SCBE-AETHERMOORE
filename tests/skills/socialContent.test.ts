/**
 * @file socialContent.test.ts
 * @module tests/skills/socialContent
 * @layer L2 (Unit Tests)
 *
 * Tests for the Post-to-X Notion Skill - social content generator
 */

import { describe, it, expect } from 'vitest';
import {
  generateTweets,
  generateBestTweet,
  generateHashtags,
  parseNotionContent,
  smartTruncate,
  MarketingContent,
  TweetOptions,
} from '../../src/skills/socialContent';

describe('socialContent', () => {
  describe('generateHashtags', () => {
    it('should generate hashtags from keywords', () => {
      const content: MarketingContent = {
        keywords: ['AI', 'Security', 'Crypto'],
      };
      const hashtags = generateHashtags(content, 3);

      expect(hashtags).toHaveLength(3);
      expect(hashtags).toContain('#AI');
      expect(hashtags).toContain('#Security');
      expect(hashtags).toContain('#Crypto');
    });

    it('should respect max hashtag limit', () => {
      const content: MarketingContent = {
        keywords: ['AI', 'Security', 'Crypto', 'Tech', 'Innovation'],
      };
      const hashtags = generateHashtags(content, 2);

      expect(hashtags).toHaveLength(2);
    });

    it('should extract hashtags from headline if no keywords', () => {
      const content: MarketingContent = {
        headline: 'Revolutionary Security Technology',
      };
      const hashtags = generateHashtags(content, 3);

      expect(hashtags.length).toBeGreaterThan(0);
      // Should extract words longer than 4 chars
      expect(hashtags.some((h) => h.includes('Revolutionary') || h.includes('Security') || h.includes('Technology'))).toBe(true);
    });

    it('should remove special characters from hashtags', () => {
      const content: MarketingContent = {
        keywords: ['AI & ML', 'Cloud-Native', 'Enterprise!'],
      };
      const hashtags = generateHashtags(content, 3);

      // No special chars in hashtags
      hashtags.forEach((h) => {
        expect(h).toMatch(/^#[a-zA-Z0-9]+$/);
      });
    });
  });

  describe('smartTruncate', () => {
    it('should not truncate short text', () => {
      const text = 'Short text here';
      expect(smartTruncate(text, 280)).toBe(text);
    });

    it('should truncate at sentence boundary when possible', () => {
      const text = 'First sentence here. Second sentence that is quite long and exceeds the limit.';
      const result = smartTruncate(text, 30);

      expect(result).toBe('First sentence here.');
      expect(result.length).toBeLessThanOrEqual(30);
    });

    it('should truncate at word boundary with ellipsis', () => {
      const text = 'This is a long sentence without periods that needs truncation somewhere';
      const result = smartTruncate(text, 30);

      expect(result.endsWith('...')).toBe(true);
      expect(result.length).toBeLessThanOrEqual(30);
    });

    it('should handle very short max length', () => {
      const text = 'Hello world';
      const result = smartTruncate(text, 5);

      expect(result.length).toBeLessThanOrEqual(5);
    });
  });

  describe('generateTweets', () => {
    const sampleContent: MarketingContent = {
      headline: 'AI Security That Actually Works',
      description: 'Post-quantum encryption for the modern era',
      sellingPoints: ['Military-grade encryption', 'Easy setup', 'Free tier available'],
      promotions: ['50% off first month with code LAUNCH50'],
      slogans: ['Security without compromise'],
      keywords: ['AI', 'Security'],
      cta: 'Try it free',
      link: 'https://example.com',
    };

    it('should generate multiple tweet variations', () => {
      const tweets = generateTweets(sampleContent);

      expect(tweets.length).toBeGreaterThan(0);
      expect(tweets.length).toBeLessThanOrEqual(4); // headline, selling, promo, slogan
    });

    it('should respect 280 character limit', () => {
      const tweets = generateTweets(sampleContent);

      tweets.forEach((tweet) => {
        expect(tweet.charCount).toBeLessThanOrEqual(280);
        expect(tweet.text.length).toBeLessThanOrEqual(280);
      });
    });

    it('should include hashtags by default', () => {
      const tweets = generateTweets(sampleContent);

      const hasHashtags = tweets.some((t) => t.hashtags.length > 0);
      expect(hasHashtags).toBe(true);
    });

    it('should skip hashtags when disabled', () => {
      const tweets = generateTweets(sampleContent, { includeHashtags: false });

      tweets.forEach((tweet) => {
        expect(tweet.hashtags).toHaveLength(0);
      });
    });

    it('should include link in tweets', () => {
      const tweets = generateTweets(sampleContent);

      const hasLink = tweets.some((t) => t.text.includes('https://example.com'));
      expect(hasLink).toBe(true);
    });

    it('should generate different styles', () => {
      const tweets = generateTweets(sampleContent);
      const styles = tweets.map((t) => t.style);

      // Should have variety
      expect(new Set(styles).size).toBeGreaterThan(1);
    });

    it('should handle minimal content', () => {
      const minimal: MarketingContent = {
        headline: 'Simple product',
      };
      const tweets = generateTweets(minimal);

      expect(tweets.length).toBeGreaterThan(0);
    });

    it('should handle description-only content', () => {
      const descOnly: MarketingContent = {
        description: 'A great product that does amazing things for your business.',
      };
      const tweets = generateTweets(descOnly);

      expect(tweets.length).toBe(1);
      expect(tweets[0].style).toBe('description');
    });

    it('should apply tone setting', () => {
      const urgentTweets = generateTweets(sampleContent, { tone: 'urgent' });
      const casualTweets = generateTweets(sampleContent, { tone: 'casual' });

      // Just verify they generate without error and have content
      expect(urgentTweets.length).toBeGreaterThan(0);
      expect(casualTweets.length).toBeGreaterThan(0);
    });

    it('should respect maxHashtags option', () => {
      const tweets = generateTweets(sampleContent, { maxHashtags: 1 });

      tweets.forEach((tweet) => {
        expect(tweet.hashtags.length).toBeLessThanOrEqual(1);
      });
    });
  });

  describe('generateBestTweet', () => {
    it('should prefer headline style', () => {
      const content: MarketingContent = {
        headline: 'Great headline',
        sellingPoints: ['Selling point'],
        promotions: ['50% off'],
      };
      const tweet = generateBestTweet(content);

      expect(tweet).not.toBeNull();
      expect(tweet!.style).toBe('headline');
    });

    it('should fallback to promotion if no headline', () => {
      const content: MarketingContent = {
        promotions: ['50% off this week only!'],
      };
      const tweet = generateBestTweet(content);

      expect(tweet).not.toBeNull();
      expect(tweet!.style).toBe('promotion');
    });

    it('should return null for empty content', () => {
      const tweet = generateBestTweet({});
      expect(tweet).toBeNull();
    });
  });

  describe('parseNotionContent', () => {
    it('should parse headline from first line', () => {
      const text = 'My Great Product\nSome description here';
      const content = parseNotionContent(text);

      expect(content.headline).toBe('My Great Product');
    });

    it('should extract bullet points as selling points', () => {
      const text = `Product Name
- Fast performance
- Easy to use
- Affordable pricing`;
      const content = parseNotionContent(text);

      expect(content.sellingPoints).toHaveLength(3);
      expect(content.sellingPoints).toContain('Fast performance');
    });

    it('should extract promotions from lines with discount keywords', () => {
      const text = `Product Name
Regular description that is long enough to be ignored
50% off this month
Use code SAVE20 for discount`;
      const content = parseNotionContent(text);

      expect(content.promotions).toBeDefined();
      expect(content.promotions!.length).toBeGreaterThan(0);
      expect(content.promotions!.some((p) => p.includes('50% off'))).toBe(true);
    });

    it('should extract hashtags from lines starting with #', () => {
      const text = `Product Name
#AI
#Security
#Tech`;
      const content = parseNotionContent(text);

      expect(content.keywords).toBeDefined();
      expect(content.keywords!.length).toBe(3);
      expect(content.keywords).toContain('AI');
      expect(content.keywords).toContain('Security');
      expect(content.keywords).toContain('Tech');
    });

    it('should extract URLs', () => {
      const text = `Product Name
Check us out at https://example.com/product`;
      const content = parseNotionContent(text);

      expect(content.link).toBe('https://example.com/product');
    });

    it('should handle empty text', () => {
      const content = parseNotionContent('');
      expect(content).toBeDefined();
    });

    it('should handle complex Notion export', () => {
      const notionExport = `SCBE-AETHERMOORE Security Suite

Post-quantum encryption for enterprise applications is amazing.

- 14-layer security pipeline
- Hyperbolic geometry risk scaling
- Easy API integration

LIMITED TIME: 30% off annual plans with code SECURE30

#Security
#PostQuantum
#Enterprise

Learn more: https://example.com`;

      const content = parseNotionContent(notionExport);

      expect(content.headline).toBe('SCBE-AETHERMOORE Security Suite');
      expect(content.sellingPoints).toHaveLength(3);
      expect(content.sellingPoints).toContain('14-layer security pipeline');
      expect(content.promotions).toBeDefined();
      expect(content.promotions!.some((p) => p.includes('30% off'))).toBe(true);
      expect(content.keywords).toBeDefined();
      expect(content.keywords).toContain('Security');
      expect(content.link).toBe('https://example.com');
    });
  });

  describe('edge cases', () => {
    it('should handle emoji in content', () => {
      const content: MarketingContent = {
        headline: '🚀 Launch Special',
        sellingPoints: ['✅ Feature one', '✅ Feature two'],
      };
      const tweets = generateTweets(content);

      expect(tweets.length).toBeGreaterThan(0);
      tweets.forEach((t) => {
        expect(t.charCount).toBeLessThanOrEqual(280);
      });
    });

    it('should handle very long selling points', () => {
      const content: MarketingContent = {
        headline: 'Product',
        sellingPoints: [
          'This is an extremely long selling point that goes on and on describing all the amazing features and benefits of our incredible product that everyone should buy right now because it is so fantastic and wonderful and amazing',
        ],
      };
      const tweets = generateTweets(content);

      tweets.forEach((t) => {
        expect(t.charCount).toBeLessThanOrEqual(280);
      });
    });

    it('should handle unicode characters', () => {
      const content: MarketingContent = {
        headline: '日本語テスト',
        keywords: ['テスト', 'Test'],
      };
      const tweets = generateTweets(content);

      expect(tweets.length).toBeGreaterThan(0);
    });
  });
});
