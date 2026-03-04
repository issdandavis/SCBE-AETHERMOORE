#!/usr/bin/env node
/*
Queue runner for n8n X+Merch ops.
Sends each queue item to an n8n webhook endpoint.
*/

import fs from 'node:fs';
import path from 'node:path';

function parseArgs(argv) {
  const out = {
    queue: 'workflows/n8n/x_ops_queue.sample.json',
    webhook: process.env.N8N_X_OPS_WEBHOOK_URL || '',
    apiKey: process.env.N8N_X_OPS_API_KEY || '',
    dryRun: false,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--queue' && argv[i + 1]) {
      out.queue = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--webhook' && argv[i + 1]) {
      out.webhook = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--api-key' && argv[i + 1]) {
      out.apiKey = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--dry-run') {
      out.dryRun = true;
      continue;
    }
  }

  return out;
}

function loadQueue(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  const data = JSON.parse(raw);
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  return [];
}

async function sendOne(webhook, apiKey, item) {
  const headers = { 'content-type': 'application/json' };
  if (apiKey) headers['x-api-key'] = apiKey;

  const resp = await fetch(webhook, {
    method: 'POST',
    headers,
    body: JSON.stringify(item),
  });

  const text = await resp.text();
  return { ok: resp.ok, status: resp.status, body: text.slice(0, 400) };
}

async function main() {
  const args = parseArgs(process.argv);
  const queuePath = path.resolve(args.queue);

  if (!fs.existsSync(queuePath)) {
    throw new Error(`Queue file not found: ${queuePath}`);
  }

  const items = loadQueue(queuePath);
  if (items.length === 0) {
    console.log('[x-ops] queue is empty');
    return;
  }

  if (!args.webhook && !args.dryRun) {
    throw new Error('Missing webhook. Set N8N_X_OPS_WEBHOOK_URL or pass --webhook');
  }

  console.log(`[x-ops] items=${items.length} webhook=${args.webhook || 'DRY-RUN-NO-WEBHOOK'}`);

  for (let i = 0; i < items.length; i += 1) {
    const item = items[i];
    if (args.dryRun) {
      console.log(`[dry-run] #${i + 1} ${JSON.stringify(item)}`);
      continue;
    }

    const res = await sendOne(args.webhook, args.apiKey, item);
    console.log(`[x-ops] #${i + 1} action=${item.action || 'post'} status=${res.status} ok=${res.ok}`);
    if (!res.ok) {
      console.log(`[x-ops] response=${res.body}`);
    }
  }
}

main().catch((err) => {
  console.error(`[x-ops] error: ${err.message}`);
  process.exit(1);
});
