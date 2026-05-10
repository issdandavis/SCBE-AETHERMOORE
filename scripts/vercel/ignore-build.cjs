#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');

// Vercel ignoreCommand contract:
//   exit 0 => skip deployment
//   exit 1 => continue deployment
//
// Keep production deploys alive for main/customer/launch branches, but skip
// preview builds when a PR only changes tests, deep docs, generated artifacts,
// training data, local agent skills, or other non-deployed repo surfaces.

const ref = process.env.VERCEL_GIT_COMMIT_REF || '';

if (
  ref === 'main' ||
  ref.startsWith('launch/') ||
  ref.startsWith('customer/') ||
  ref.startsWith('vercel-test/')
) {
  console.log(`vercel-build: deploy branch '${ref}'`);
  process.exit(1);
}

function git(args) {
  return spawnSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

let base = process.env.VERCEL_GIT_PREVIOUS_SHA || '';
if (!base || git(['cat-file', '-e', `${base}^{commit}`]).status !== 0) {
  base = 'HEAD^';
}

const relevantPaths = [
  'vercel.json',
  'package.json',
  'package-lock.json',
  'api/agent',
  'api/polly',
  'api/billing',
  'docs/offers.json',
  'docs/governance-snapshot.html',
  'docs/hire.html',
  'docs/hire-b.html',
  'docs/service-credits.html',
  'docs/supporter.html',
  'docs/hosted-run.html',
  'docs/polly-stats.html',
  'docs/static',
  'docs/product-manual',
];

const diff = git(['diff', '--quiet', base, 'HEAD', '--', ...relevantPaths]);

if (diff.status === 0) {
  console.log('vercel-build: skip; no deployed paths changed');
  process.exit(0);
}

if (diff.status === 1) {
  console.log('vercel-build: deploy; deployed paths changed');
  process.exit(1);
}

console.error(diff.stderr || 'vercel-build: git diff failed; deploying to be safe');
process.exit(1);
