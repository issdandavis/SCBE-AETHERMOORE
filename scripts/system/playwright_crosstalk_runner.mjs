#!/usr/bin/env node
/**
 * SCBE Playwright Cross-Talk Runner.
 *
 * Browser evidence is gathered once, then reviewed by multiple local or
 * external "model" lanes. External lanes are command adapters: pass
 * `--reviewer-command name=command` and the command receives page evidence as
 * JSON on stdin and may return JSON on stdout.
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const DEFAULT_BASE_URL = 'https://scbe-agent-bridge-vercel.vercel.app';
const DEFAULT_OUT_DIR = 'output/playwright/crosstalk';
const DEFAULT_TARGETS = [
  {
    id: 'products',
    path: '/products',
    viewports: ['desktop', 'mobile'],
    expects: ['Best first paid move', 'Why this is priced lower', 'Free 60-second self-check'],
    requiresCheckout: true,
    actions: [
      { type: 'click', selector: 'button[data-answer="read"]', label: 'choose written read' },
      { type: 'click', selector: 'button[data-answer="once"]', label: 'choose one-time payment' },
      {
        type: 'expectText',
        text: 'AI Governance Snapshot',
        label: 'picker recommends paid snapshot',
      },
    ],
  },
  {
    id: 'start-here',
    path: '/start-here',
    viewports: ['desktop', 'mobile'],
    expects: ['Most commercial visitors should start', 'Buy Snapshot $500'],
    requiresCheckout: true,
  },
  {
    id: 'hire-lead-dryrun',
    path: '/hire',
    viewports: ['desktop'],
    expects: ['Email or phone', 'Send to Issac'],
    requiresCheckout: false,
    actions: [
      {
        type: 'fill',
        selector: '#leadContact',
        value: 'playwright-smoke@example.com',
        label: 'enter contact',
      },
      {
        type: 'select',
        selector: '#leadProjectType',
        value: 'audit',
        label: 'choose audit project type',
      },
      { type: 'select', selector: '#leadBudget', value: '5k-15k', label: 'choose audit budget' },
      {
        type: 'select',
        selector: '#leadTimeline',
        value: 'asap',
        label: 'choose this week timeline',
      },
      {
        type: 'fill',
        selector: '#leadDescription',
        value:
          'Automated dry-run: verify the lead form can accept a concrete AI governance request.',
        label: 'enter lead description',
      },
      { type: 'expectText', text: 'Send to Issac', label: 'lead form remains ready to submit' },
    ],
  },
];

const VIEWPORTS = {
  desktop: { width: 1366, height: 900 },
  mobile: { width: 390, height: 844 },
};

function parseArgs(argv) {
  const args = {
    baseUrl: DEFAULT_BASE_URL,
    outDir: DEFAULT_OUT_DIR,
    targets: [],
    reviewerCommands: [],
    timeoutMs: 45000,
    dryRunForms: true,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--base-url' && next) {
      args.baseUrl = next;
      i += 1;
    } else if (arg === '--out-dir' && next) {
      args.outDir = next;
      i += 1;
    } else if (arg === '--target' && next) {
      args.targets.push(parseTarget(next));
      i += 1;
    } else if (arg === '--reviewer-command' && next) {
      args.reviewerCommands.push(parseReviewerCommand(next));
      i += 1;
    } else if (arg === '--timeout-ms' && next) {
      args.timeoutMs = Number.parseInt(next, 10);
      i += 1;
    } else if (arg === '--execute-forms') {
      args.dryRunForms = false;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown or incomplete argument: ${arg}`);
    }
  }

  if (args.targets.length === 0) args.targets = DEFAULT_TARGETS;
  return args;
}

function parseTarget(spec) {
  const [idPath, expectsRaw = ''] = spec.split('::');
  const [id, urlPath = idPath] = idPath.includes('=')
    ? idPath.split('=')
    : [slugFromPath(idPath), idPath];
  return {
    id,
    path: urlPath,
    viewports: ['desktop', 'mobile'],
    expects: expectsRaw
      .split('|')
      .map((x) => x.trim())
      .filter(Boolean),
  };
}

function parseReviewerCommand(spec) {
  const eq = spec.indexOf('=');
  if (eq <= 0) throw new Error(`Reviewer command must look like name=command, got: ${spec}`);
  return { id: spec.slice(0, eq), command: spec.slice(eq + 1) };
}

function slugFromPath(value) {
  return value
    .replace(/^https?:\/\//, '')
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
}

function printHelp() {
  console.log(`Usage:
  node scripts/system/playwright_crosstalk_runner.mjs [options]

Options:
  --base-url URL                     Base URL for relative targets
  --out-dir DIR                      Output directory (default: ${DEFAULT_OUT_DIR})
  --target id=/path::copy|to|expect  Add target; repeatable
  --reviewer-command name=command    External reviewer command; repeatable
  --timeout-ms N                     Page navigation timeout
  --execute-forms                    Allow submit actions instead of dry-run fill only

External reviewer commands receive one page evidence JSON object on stdin.
They may return {"score":0.8,"verdict":"pass","findings":["..."]}.
`);
}

function absolutize(baseUrl, targetPath) {
  if (/^https?:\/\//i.test(targetPath)) return targetPath;
  return `${baseUrl.replace(/\/$/, '')}/${targetPath.replace(/^\//, '')}`;
}

async function executeActions(page, target, args) {
  const results = [];
  for (const action of target.actions || []) {
    const startedAt = new Date().toISOString();
    try {
      if (action.type === 'fill') {
        await page
          .locator(action.selector)
          .fill(action.value || '', { timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'select') {
        await page
          .locator(action.selector)
          .selectOption(action.value || '', { timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'check') {
        await page.locator(action.selector).check({ timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'uncheck') {
        await page.locator(action.selector).uncheck({ timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'click') {
        await page.locator(action.selector).click({ timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'press') {
        await page
          .locator(action.selector || 'body')
          .press(action.key || 'Enter', { timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'submit') {
        if (args.dryRunForms || action.dryRun === true) {
          results.push({
            type: action.type,
            label: action.label || action.selector || 'submit',
            skipped: true,
            ok: true,
            reason: 'dry-run form mode; pass --execute-forms to submit',
            startedAt,
            finishedAt: new Date().toISOString(),
          });
          continue;
        }
        await page.locator(action.selector).click({ timeout: action.timeoutMs || 10000 });
      } else if (action.type === 'expectText') {
        const body = await page.locator('body').innerText({ timeout: action.timeoutMs || 10000 });
        if (!body.includes(action.text || ''))
          throw new Error(`expected text not found: ${action.text}`);
      } else if (action.type === 'waitForSelector') {
        await page.locator(action.selector).waitFor({ timeout: action.timeoutMs || 10000 });
      } else {
        throw new Error(`unsupported action type: ${action.type}`);
      }
      results.push({
        type: action.type,
        label: action.label || action.selector || action.text || action.type,
        ok: true,
        skipped: false,
        startedAt,
        finishedAt: new Date().toISOString(),
      });
    } catch (error) {
      results.push({
        type: action.type,
        label: action.label || action.selector || action.text || action.type,
        ok: false,
        skipped: false,
        error: String(error?.message || error),
        startedAt,
        finishedAt: new Date().toISOString(),
      });
    }
  }
  return results;
}

async function collectPageEvidence(browser, target, viewportName, args) {
  const viewport = VIEWPORTS[viewportName];
  if (!viewport) throw new Error(`Unknown viewport: ${viewportName}`);

  const page = await browser.newPage({ viewport });
  const pageErrors = [];
  const consoleErrors = [];
  const failedRequests = [];

  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('requestfailed', (request) => {
    failedRequests.push({
      url: request.url(),
      failure: request.failure()?.errorText || 'request_failed',
    });
  });

  const url = absolutize(args.baseUrl, target.path);
  const response = await page.goto(url, { waitUntil: 'networkidle', timeout: args.timeoutMs });
  const beforeScreenshotPath = path.join(args.outDir, `${target.id}-${viewportName}-before.png`);
  await page.screenshot({ path: beforeScreenshotPath, fullPage: true });
  const actionResults = await executeActions(page, target, args);
  if (actionResults.length > 0) {
    await page.waitForTimeout(350);
  }
  const bodyText = await page
    .locator('body')
    .innerText({ timeout: 10000 })
    .catch(() => '');
  const title = await page.title().catch(() => '');
  const h1 = await page
    .locator('h1')
    .first()
    .innerText({ timeout: 10000 })
    .catch(() => '');
  const links = await page
    .locator('a')
    .evaluateAll((nodes) =>
      nodes.map((node) => ({
        text: (node.textContent || '').trim().replace(/\s+/g, ' '),
        href: node.href,
      }))
    )
    .catch(() => []);
  const inputSnapshot = await page
    .locator('input, textarea, select')
    .evaluateAll((nodes) =>
      nodes
        .filter((node) => node.id || node.name)
        .map((node) => ({
          id: node.id || '',
          name: node.name || '',
          tag: node.tagName.toLowerCase(),
          type: node.getAttribute('type') || '',
          valueLength: typeof node.value === 'string' ? node.value.length : 0,
          hasValue: Boolean(node.value),
        }))
    )
    .catch(() => []);
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
    bodyLength: document.body?.innerText?.length || 0,
  }));

  const screenshotPath = path.join(args.outDir, `${target.id}-${viewportName}-after.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.close();

  const expectedCopyMissing = target.expects.filter((text) => !bodyText.includes(text));
  const stripeLinks = links.filter((link) =>
    /^(https?:\/\/)?([^/?#]+\.)?(stripe\.com|buy\.stripe\.com)([/?#]|$)/i.test(link.href)
  );

  return {
    targetId: target.id,
    viewport: viewportName,
    url,
    status: response?.status() || 0,
    title,
    h1,
    expectedCopyMissing,
    requiresCheckout: target.requiresCheckout !== false,
    actionResults,
    actionOk: actionResults.every((item) => item.ok),
    workDoneCount: actionResults.filter((item) => item.ok && !item.skipped).length,
    skippedActionCount: actionResults.filter((item) => item.skipped).length,
    inputSnapshot,
    stripeLinkCount: stripeLinks.length,
    firstStripeLinks: stripeLinks.slice(0, 5),
    overflowPx: metrics.scrollWidth - metrics.viewportWidth,
    bodyLength: metrics.bodyLength,
    pageErrors,
    consoleErrors,
    failedRequests,
    beforeScreenshotPath: beforeScreenshotPath.replaceAll('\\', '/'),
    screenshotPath: screenshotPath.replaceAll('\\', '/'),
  };
}

export function runBuiltInReviewers(evidence) {
  return [commerceReviewer(evidence), uxReviewer(evidence), technicalReviewer(evidence)];
}

function commerceReviewer(evidence) {
  const findings = [];
  let score = 1;
  if (evidence.expectedCopyMissing.length > 0) {
    score -= 0.35;
    findings.push(`missing expected offer copy: ${evidence.expectedCopyMissing.join('; ')}`);
  }
  if (evidence.requiresCheckout && evidence.stripeLinkCount === 0) {
    score -= 0.35;
    findings.push('no Stripe checkout links found');
  }
  if ((evidence.actionResults || []).some((item) => !item.ok)) {
    score -= 0.3;
    findings.push('one or more customer workflow actions failed');
  }
  if ((evidence.workDoneCount || 0) === 0 && (evidence.actionResults || []).length > 0) {
    score -= 0.2;
    findings.push('workflow had actions but completed no non-skipped work');
  }
  if (
    (evidence.actionResults || []).some((item) =>
      ['fill', 'select', 'check'].includes(item.type)
    ) &&
    !hasCapturedInputValue(evidence)
  ) {
    score -= 0.25;
    findings.push('input actions ran but no filled values were captured');
  }
  if (!/\$|price|paid|buy|snapshot|supporter/i.test(`${evidence.h1} ${evidence.title}`)) {
    score -= 0.1;
    findings.push('commercial intent is not visible in title or primary heading');
  }
  return vote('model.commerce-heuristic', score, findings);
}

function hasCapturedInputValue(evidence) {
  return (evidence.inputSnapshot || []).some((item) => item.hasValue || item.valueLength > 0);
}

function uxReviewer(evidence) {
  const findings = [];
  let score = 1;
  if (!evidence.h1) {
    score -= 0.25;
    findings.push('missing h1');
  }
  if (evidence.overflowPx > 2) {
    score -= 0.3;
    findings.push(`horizontal overflow ${evidence.overflowPx}px`);
  }
  if (evidence.bodyLength < 800) {
    score -= 0.15;
    findings.push('page body looks thin for a customer decision page');
  }
  if ((evidence.actionResults || []).length > 0 && !evidence.actionOk) {
    score -= 0.25;
    findings.push('interactive path did not complete cleanly');
  }
  return vote('model.ux-heuristic', score, findings);
}

function technicalReviewer(evidence) {
  const findings = [];
  let score = 1;
  if (evidence.status !== 200) {
    score -= 0.55;
    findings.push(`http status ${evidence.status}`);
  }
  if (evidence.pageErrors.length > 0) {
    score -= 0.25;
    findings.push(`page errors: ${evidence.pageErrors.slice(0, 3).join('; ')}`);
  }
  if (evidence.consoleErrors.length > 0) {
    score -= 0.1;
    findings.push(`console errors: ${evidence.consoleErrors.slice(0, 3).join('; ')}`);
  }
  if (!evidence.actionOk) {
    score -= 0.3;
    findings.push('browser action execution failed');
  }
  return vote('model.technical-heuristic', score, findings);
}

function vote(reviewer, score, findings) {
  const normalized = Math.max(0, Math.min(1, Number(score.toFixed(3))));
  return {
    reviewer,
    score: normalized,
    verdict: normalized >= 0.8 ? 'pass' : normalized >= 0.55 ? 'warn' : 'fail',
    findings: findings.length > 0 ? findings : ['no blocking issue found'],
  };
}

async function runExternalReviewer(commandSpec, evidence) {
  return new Promise((resolve) => {
    const child = spawn(commandSpec.command, {
      shell: true,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      resolve(vote(`model.${commandSpec.id}`, 0, [`reviewer command failed: ${error.message}`]));
    });
    child.on('close', (code) => {
      if (code !== 0) {
        resolve(vote(`model.${commandSpec.id}`, 0, [`reviewer exited ${code}: ${stderr.trim()}`]));
        return;
      }
      try {
        const parsed = JSON.parse(stdout);
        resolve(
          vote(
            `model.${commandSpec.id}`,
            typeof parsed.score === 'number' ? parsed.score : 0.5,
            Array.isArray(parsed.findings)
              ? parsed.findings
              : [parsed.verdict || 'external reviewer returned JSON']
          )
        );
      } catch (error) {
        resolve(
          vote(`model.${commandSpec.id}`, 0.4, [
            `reviewer returned non-JSON output: ${stdout.slice(0, 160)}`,
          ])
        );
      }
    });
    child.stdin.end(JSON.stringify(evidence));
  });
}

export function aggregateVotes(votes) {
  const scores = votes.map((item) => item.score);
  const averageScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const verdict =
    votes.some((item) => item.verdict === 'fail') || averageScore < 0.55
      ? 'fail'
      : votes.some((item) => item.verdict === 'warn') || averageScore < 0.8
        ? 'warn'
        : 'pass';
  return {
    averageScore: Number(averageScore.toFixed(3)),
    verdict,
    failingReviewers: votes.filter((item) => item.verdict === 'fail').map((item) => item.reviewer),
    warningReviewers: votes.filter((item) => item.verdict === 'warn').map((item) => item.reviewer),
  };
}

function writeMarkdown(report, outDir) {
  const lines = [
    '# Playwright Cross-Talk Report',
    '',
    `Generated: ${report.generatedAt}`,
    `Base URL: ${report.baseUrl}`,
    `Overall verdict: ${report.summary.verdict}`,
    `Average score: ${report.summary.averageScore}`,
    '',
    '## Pages',
    '',
  ];

  for (const page of report.pages) {
    lines.push(`### ${page.evidence.targetId} / ${page.evidence.viewport}`);
    lines.push('');
    lines.push(`- URL: ${page.evidence.url}`);
    lines.push(`- Status: ${page.evidence.status}`);
    lines.push(`- H1: ${page.evidence.h1 || '(none)'}`);
    lines.push(`- Screenshot: ${page.evidence.screenshotPath}`);
    lines.push(
      `- Work done: ${page.evidence.workDoneCount} action(s), ${page.evidence.skippedActionCount} skipped`
    );
    lines.push(`- Aggregate: ${page.aggregate.verdict} (${page.aggregate.averageScore})`);
    for (const action of page.evidence.actionResults || []) {
      lines.push(
        `- action ${action.ok ? 'ok' : 'failed'}${action.skipped ? ' (skipped)' : ''}: ${action.label}${
          action.error ? ` — ${action.error}` : ''
        }`
      );
    }
    for (const voteItem of page.votes) {
      lines.push(
        `- ${voteItem.reviewer}: ${voteItem.verdict} (${voteItem.score}) — ${voteItem.findings.join('; ')}`
      );
    }
    lines.push('');
  }

  const markdownPath = path.join(outDir, 'crosstalk-report.md');
  fs.writeFileSync(markdownPath, `${lines.join('\n')}\n`, 'utf8');
  return markdownPath.replaceAll('\\', '/');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  fs.mkdirSync(args.outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const pages = [];
  try {
    for (const target of args.targets) {
      for (const viewport of target.viewports) {
        const evidence = await collectPageEvidence(browser, target, viewport, args);
        const builtInVotes = runBuiltInReviewers(evidence);
        const externalVotes = [];
        for (const commandSpec of args.reviewerCommands) {
          externalVotes.push(await runExternalReviewer(commandSpec, evidence));
        }
        const votes = [...builtInVotes, ...externalVotes];
        pages.push({ evidence, votes, aggregate: aggregateVotes(votes) });
      }
    }
  } finally {
    await browser.close();
  }

  const allVotes = pages.flatMap((page) => page.votes);
  const summary = aggregateVotes(allVotes);
  const report = {
    schema: 'scbe.playwright.crosstalk.v1',
    generatedAt: new Date().toISOString(),
    baseUrl: args.baseUrl,
    reviewerCommands: args.reviewerCommands.map((item) => item.id),
    summary,
    pages,
  };
  const jsonPath = path.join(args.outDir, 'crosstalk-report.json');
  fs.writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  const markdownPath = writeMarkdown(report, args.outDir);

  console.log(
    JSON.stringify(
      {
        verdict: summary.verdict,
        averageScore: summary.averageScore,
        pages: pages.length,
        json: jsonPath.replaceAll('\\', '/'),
        markdown: markdownPath,
      },
      null,
      2
    )
  );

  if (summary.verdict === 'fail') process.exitCode = 1;
}

if (fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main().catch((error) => {
    const message = String(error?.message || error);
    if (/Executable doesn't exist|playwright install/i.test(message)) {
      console.error(`${message}\n\nFix: npx playwright install chromium`);
    } else {
      console.error(message);
    }
    process.exit(1);
  });
}
