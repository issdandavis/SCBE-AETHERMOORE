#!/usr/bin/env node
'use strict';

// Vercel ignoreCommand contract:
//   exit 0 => skip deployment
//   exit 1 => continue deployment
//
// Keep production deploys alive for main/customer/launch branches, but skip
// preview builds when a PR only changes tests, deep docs, generated artifacts,
// training data, local agent skills, or other non-deployed repo surfaces.

const ref = process.env.VERCEL_GIT_COMMIT_REF || '';
const repoOwner = process.env.VERCEL_GIT_REPO_OWNER || 'issdandavis';
const repoSlug = process.env.VERCEL_GIT_REPO_SLUG || 'SCBE-AETHERMOORE';
const prId = process.env.VERCEL_GIT_PULL_REQUEST_ID || '';
const currentSha = process.env.VERCEL_GIT_COMMIT_SHA || '';
const previousSha = process.env.VERCEL_GIT_PREVIOUS_SHA || '';

const relevantPaths = [
  '.vercelignore',
  'vercel.json',
  'package.json',
  'package-lock.json',
  'scripts/vercel/ignore-build.cjs',
  'api/agent',
  'api/polly',
  'api/billing',
  'docs/offers.json',
  'docs/governance-snapshot.html',
  'docs/hire.html',
  'docs/hire-b.html',
  'docs/products.html',
  'docs/start-here.html',
  'docs/agents.html',
  'docs/chat.html',
  'docs/payments.html',
  'docs/workflow-snapshot.html',
  'docs/service-credits.html',
  'docs/supporter.html',
  'docs/hosted-run.html',
  'docs/legal/privacy.html',
  'docs/legal/terms.html',
  'docs/polly-stats.html',
  'docs/static',
  'docs/product-manual',
];

function isRelevant(path) {
  return relevantPaths.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

function finish(files) {
  const changed = files.filter(Boolean);
  if (!changed.some(isRelevant)) {
    console.log('vercel-build: skip; no deployed paths changed');
    return 0;
  }

  console.log('vercel-build: deploy; deployed paths changed');
  return 1;
}

async function githubJson(path) {
  const response = await fetch(`https://api.github.com${path}`, {
    headers: {
      Accept: 'application/vnd.github+json',
      'User-Agent': 'scbe-vercel-ignore-build',
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub API ${response.status} for ${path}`);
  }
  return response.json();
}

async function prFiles() {
  const files = [];
  let page = 1;
  while (page <= 10) {
    const batch = await githubJson(
      `/repos/${repoOwner}/${repoSlug}/pulls/${prId}/files?per_page=100&page=${page}`,
    );
    if (!Array.isArray(batch) || batch.length === 0) break;
    files.push(...batch.map((item) => item.filename));
    if (batch.length < 100) break;
    page += 1;
  }
  return files;
}

async function compareFiles() {
  if (!previousSha || !currentSha) return null;
  const compare = await githubJson(
    `/repos/${repoOwner}/${repoSlug}/compare/${previousSha}...${currentSha}`,
  );
  if (!Array.isArray(compare.files)) return null;
  return compare.files.map((item) => item.filename);
}

async function main() {
  if (
    ref === 'main' ||
    ref.startsWith('launch/') ||
    ref.startsWith('customer/') ||
    ref.startsWith('vercel-test/')
  ) {
    console.log(`vercel-build: deploy branch '${ref}'`);
    return 1;
  }

  if (process.env.SCBE_VERCEL_CHANGED_FILES) {
    return finish(process.env.SCBE_VERCEL_CHANGED_FILES.split(/[\r\n,]+/).map((item) => item.trim()));
  }

  try {
    if (prId) {
      return finish(await prFiles());
    }

    const files = await compareFiles();
    if (files) return finish(files);

    console.log('vercel-build: deploy; no PR or compare metadata available');
    return 1;
  } catch (error) {
    console.error(`vercel-build: deploy; path check failed: ${error.message || error}`);
    return 1;
  }
}

main().then((code) => {
  process.exitCode = code;
});
