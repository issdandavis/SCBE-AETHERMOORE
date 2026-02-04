#!/usr/bin/env node
/**
 * @file tweet-cli.ts
 * @module skills/tweet-cli
 * @component Tweet Generator CLI
 * @version 1.0.0
 *
 * Quick CLI to generate tweets from marketing content.
 *
 * Usage:
 *   npx ts-node src/skills/tweet-cli.ts "Your headline" --selling "Point 1" --promo "50% off"
 *   npx ts-node src/skills/tweet-cli.ts --file notion-content.txt
 */

import * as fs from 'fs';
import {
  generateTweets,
  parseNotionContent,
  MarketingContent,
  TweetOptions,
} from './socialContent';

interface CliArgs {
  headline?: string;
  description?: string;
  sellingPoints: string[];
  promotions: string[];
  keywords: string[];
  slogans: string[];
  cta?: string;
  link?: string;
  file?: string;
  tone: 'casual' | 'professional' | 'urgent' | 'playful';
  noHashtags: boolean;
  maxHashtags: number;
  help: boolean;
}

function printHelp(): void {
  console.log(`
Tweet Generator CLI - Create X/Twitter posts from your marketing content

USAGE:
  npx ts-node src/skills/tweet-cli.ts [options] [headline]

OPTIONS:
  --headline, -h TEXT     Main headline/hook
  --desc, -d TEXT         Product description
  --selling, -s TEXT      Selling point (can use multiple)
  --promo, -p TEXT        Promotion/offer (can use multiple)
  --keyword, -k TEXT      Keyword for hashtags (can use multiple)
  --slogan TEXT           Brand slogan
  --cta TEXT              Call to action (e.g., "Try it free")
  --link, -l URL          Link to include
  --file, -f PATH         Read content from file (Notion export)
  --tone casual|pro|urgent|playful
                          Tweet tone (default: professional)
  --no-hashtags           Skip hashtags
  --max-hashtags N        Max hashtags (default: 3)
  --help                  Show this help

EXAMPLES:
  # Quick headline tweet
  npx ts-node src/skills/tweet-cli.ts "AI Security That Works" --link https://example.com

  # Full marketing content
  npx ts-node src/skills/tweet-cli.ts \\
    --headline "Launch Special" \\
    --selling "Military-grade encryption" \\
    --selling "Easy setup" \\
    --promo "50% off with code LAUNCH" \\
    --keyword AI --keyword Security \\
    --cta "Try free" \\
    --link https://example.com

  # From Notion export file
  npx ts-node src/skills/tweet-cli.ts --file my-ad-content.txt
`);
}

function parseArgs(args: string[]): CliArgs {
  const result: CliArgs = {
    sellingPoints: [],
    promotions: [],
    keywords: [],
    slogans: [],
    tone: 'professional',
    noHashtags: false,
    maxHashtags: 3,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const next = args[i + 1];

    switch (arg) {
      case '--help':
        result.help = true;
        break;
      case '--headline':
      case '-h':
        result.headline = next;
        i++;
        break;
      case '--desc':
      case '-d':
        result.description = next;
        i++;
        break;
      case '--selling':
      case '-s':
        result.sellingPoints.push(next);
        i++;
        break;
      case '--promo':
      case '-p':
        result.promotions.push(next);
        i++;
        break;
      case '--keyword':
      case '-k':
        result.keywords.push(next);
        i++;
        break;
      case '--slogan':
        result.slogans.push(next);
        i++;
        break;
      case '--cta':
        result.cta = next;
        i++;
        break;
      case '--link':
      case '-l':
        result.link = next;
        i++;
        break;
      case '--file':
      case '-f':
        result.file = next;
        i++;
        break;
      case '--tone':
        result.tone = next as CliArgs['tone'];
        i++;
        break;
      case '--no-hashtags':
        result.noHashtags = true;
        break;
      case '--max-hashtags':
        result.maxHashtags = parseInt(next, 10);
        i++;
        break;
      default:
        // Positional argument = headline
        if (!arg.startsWith('-') && !result.headline) {
          result.headline = arg;
        }
    }
  }

  return result;
}

function main(): void {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    printHelp();
    process.exit(0);
  }

  let content: MarketingContent;

  // Load from file if specified
  if (args.file) {
    if (!fs.existsSync(args.file)) {
      console.error(`Error: File not found: ${args.file}`);
      process.exit(1);
    }
    const fileContent = fs.readFileSync(args.file, 'utf-8');
    content = parseNotionContent(fileContent);

    // Override with CLI args
    if (args.headline) content.headline = args.headline;
    if (args.description) content.description = args.description;
    if (args.sellingPoints.length > 0) content.sellingPoints = args.sellingPoints;
    if (args.promotions.length > 0) content.promotions = args.promotions;
    if (args.keywords.length > 0) content.keywords = args.keywords;
    if (args.slogans.length > 0) content.slogans = args.slogans;
    if (args.cta) content.cta = args.cta;
    if (args.link) content.link = args.link;
  } else {
    // Build from CLI args
    content = {
      headline: args.headline,
      description: args.description,
      sellingPoints: args.sellingPoints.length > 0 ? args.sellingPoints : undefined,
      promotions: args.promotions.length > 0 ? args.promotions : undefined,
      keywords: args.keywords.length > 0 ? args.keywords : undefined,
      slogans: args.slogans.length > 0 ? args.slogans : undefined,
      cta: args.cta,
      link: args.link,
    };
  }

  // Check if we have any content
  if (!content.headline && !content.description && !content.sellingPoints && !content.promotions) {
    console.error('Error: No content provided. Use --help for usage.');
    process.exit(1);
  }

  const options: TweetOptions = {
    tone: args.tone,
    includeHashtags: !args.noHashtags,
    maxHashtags: args.maxHashtags,
  };

  const tweets = generateTweets(content, options);

  if (tweets.length === 0) {
    console.error('Error: Could not generate tweets from the provided content.');
    process.exit(1);
  }

  // Output tweets
  console.log('\n📱 Generated Tweets:\n');
  console.log('─'.repeat(50));

  for (let i = 0; i < tweets.length; i++) {
    const tweet = tweets[i];
    console.log(`\n[${i + 1}] ${tweet.style.toUpperCase()} STYLE (${tweet.charCount}/280 chars)\n`);
    console.log(tweet.text);
    console.log('\n' + '─'.repeat(50));
  }

  console.log('\n✅ Copy any tweet above and paste to X/Twitter!\n');
}

main();
