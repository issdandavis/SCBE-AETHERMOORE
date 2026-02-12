#!/usr/bin/env node

const fs = require('fs/promises');
const path = require('path');
const { Client } = require('@notionhq/client');

const CONFIG_PATH = path.resolve(__dirname, 'sync-config.json');

function parseArgs(argv) {
  const args = { all: false };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];

    if (token === '--all') {
      args.all = true;
      continue;
    }

    if (token === '--page-id') {
      args.pageId = argv[++i];
      continue;
    }

    if (token === '--output') {
      args.output = argv[++i];
      continue;
    }

    if (token === '--config-key') {
      args.configKey = argv[++i];
      continue;
    }
  }

  return args;
}

function textFromRichText(richText = []) {
  return richText.map((part) => part.plain_text || '').join('');
}

function toBulletedLine(text, depth = 0) {
  return `${'  '.repeat(depth)}- ${text}`.trimEnd();
}

function toNumberedLine(text, index, depth = 0) {
  return `${'  '.repeat(depth)}${index}. ${text}`.trimEnd();
}

async function getAllBlocks(notion, blockId) {
  const results = [];
  let cursor;

  do {
    const response = await notion.blocks.children.list({
      block_id: blockId,
      start_cursor: cursor,
      page_size: 100
    });

    results.push(...response.results);
    cursor = response.has_more ? response.next_cursor : undefined;
  } while (cursor);

  return results;
}

async function blockToMarkdown(notion, block, depth = 0, numberedIndex = 1) {
  const type = block.type;
  const value = block[type] || {};

  switch (type) {
    case 'paragraph':
      return `${textFromRichText(value.rich_text)}\n`;
    case 'heading_1':
      return `# ${textFromRichText(value.rich_text)}\n`;
    case 'heading_2':
      return `## ${textFromRichText(value.rich_text)}\n`;
    case 'heading_3':
      return `### ${textFromRichText(value.rich_text)}\n`;
    case 'bulleted_list_item':
      return `${toBulletedLine(textFromRichText(value.rich_text), depth)}\n`;
    case 'numbered_list_item':
      return `${toNumberedLine(textFromRichText(value.rich_text), numberedIndex, depth)}\n`;
    case 'to_do': {
      const checked = value.checked ? '[x]' : '[ ]';
      return `- ${checked} ${textFromRichText(value.rich_text)}\n`;
    }
    case 'quote':
      return `> ${textFromRichText(value.rich_text)}\n`;
    case 'code': {
      const language = value.language || 'text';
      return `\n\`\`\`${language}\n${textFromRichText(value.rich_text)}\n\`\`\`\n`;
    }
    case 'divider':
      return '\n---\n';
    default:
      return `<!-- Unsupported block type: ${type} -->\n`;
  }
}

async function blocksToMarkdown(notion, blocks, depth = 0) {
  let markdown = '';
  let numberCounter = 1;

  for (const block of blocks) {
    if (block.type !== 'numbered_list_item') {
      numberCounter = 1;
    }

    markdown += await blockToMarkdown(
      notion,
      block,
      depth,
      block.type === 'numbered_list_item' ? numberCounter : 1
    );

    if (block.type === 'numbered_list_item') {
      numberCounter += 1;
    }

    if (block.has_children) {
      const children = await getAllBlocks(notion, block.id);
      markdown += await blocksToMarkdown(notion, children, depth + 1);
    }

    markdown += '\n';
  }

  return markdown.replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
}

async function fetchPageTitle(notion, pageId) {
  const page = await notion.pages.retrieve({ page_id: pageId });

  const property = Object.values(page.properties || {}).find(
    (prop) => prop.type === 'title' && Array.isArray(prop.title)
  );

  return property ? textFromRichText(property.title) : `Notion Page ${pageId}`;
}

async function loadConfig() {
  const raw = await fs.readFile(CONFIG_PATH, 'utf8');
  return JSON.parse(raw);
}

async function ensureDocsPath(filePath) {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
}

async function syncSinglePage(notion, pageId, outputPath) {
  const cleanPageId = pageId.replace(/-/g, '');
  const blocks = await getAllBlocks(notion, cleanPageId);
  const title = await fetchPageTitle(notion, cleanPageId);
  const markdown = await blocksToMarkdown(notion, blocks);

  const content = `# ${title}\n\n${markdown}`;
  const resolvedOutput = path.resolve(process.cwd(), outputPath);

  await ensureDocsPath(resolvedOutput);
  await fs.writeFile(resolvedOutput, content, 'utf8');

  console.log(`Synced ${cleanPageId} -> ${outputPath}`);
}

function resolveConfigEntry(config, key) {
  if (!key) return null;

  if (!config[key]) {
    throw new Error(`Config key "${key}" not found in scripts/sync-config.json`);
  }

  return config[key];
}

async function main() {
  const notionApiKey = process.env.NOTION_API_KEY;
  if (!notionApiKey) {
    throw new Error('Missing NOTION_API_KEY environment variable.');
  }

  const args = parseArgs(process.argv.slice(2));
  const notion = new Client({ auth: notionApiKey });
  const config = await loadConfig();

  if (args.all) {
    const entries = Object.entries(config);
    for (const [key, { pageId, outputPath }] of entries) {
      if (!pageId || pageId.startsWith('REPLACE_WITH_')) {
        console.warn(`Skipping ${key}: missing real Notion page ID.`);
        continue;
      }

      await syncSinglePage(notion, pageId, outputPath);
    }
    return;
  }

  if (args.configKey) {
    const entry = resolveConfigEntry(config, args.configKey);
    await syncSinglePage(notion, entry.pageId, args.output || entry.outputPath);
    return;
  }

  if (args.pageId && args.output) {
    await syncSinglePage(notion, args.pageId, args.output);
    return;
  }

  throw new Error(
    'Usage: node scripts/notion-sync.js (--all | --config-key <key> [--output <path>] | --page-id <id> --output <path>)'
  );
}

main().catch((error) => {
  console.error(`Notion sync failed: ${error.message}`);
  process.exit(1);
});
