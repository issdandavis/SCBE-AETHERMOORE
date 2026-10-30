'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  automationMarker,
  isManagedIssue,
  reconcileRollingIssue,
} = require('../../.github/scripts/issue-lifecycle.cjs');
const { classifyIssue } = require('../../.github/scripts/issue-triage.cjs');

const context = { repo: { owner: 'issdandavis', repo: 'SCBE-AETHERMOORE' } };

function fakeGitHub(issues = []) {
  const calls = { create: [], update: [], list: [] };
  const api = {
    paginate: async (_method, params) => {
      calls.list.push(params);
      return issues;
    },
    rest: {
      issues: {
        listForRepo: async (params) => ({ data: issues, params }),
        create: async (params) => {
          calls.create.push(params);
          return { data: { number: 99 } };
        },
        update: async (params) => {
          calls.update.push(params);
          return { data: params };
        },
      },
    },
  };
  return { api, calls };
}

test('creates one marked rolling issue with normalized labels', async () => {
  const { api, calls } = fakeGitHub();
  const result = await reconcileRollingIssue({
    github: api,
    context,
    key: 'repo-health',
    label: 'repo-health',
    title: 'Repo Health - action required',
    active: true,
    body: 'A check failed.',
    labels: ['automated', 'repo-health'],
  });

  assert.equal(result.created, true);
  assert.equal(result.issueNumber, 99);
  assert.equal(calls.create.length, 1);
  assert.match(calls.create[0].body, /^<!-- scbe-automation:repo-health -->/);
  assert.deepEqual(calls.create[0].labels, ['repo-health', 'automated']);
});

test('updates the current issue and closes managed duplicates', async () => {
  const marker = automationMarker('nightly-python');
  const issues = [
    {
      number: 10,
      title: 'Nightly full Python suite failed',
      body: `${marker}\nold`,
      user: { login: 'github-actions[bot]', type: 'Bot' },
    },
    {
      number: 11,
      title: 'Nightly full Python suite failed - old',
      body: `${marker}\nolder`,
      user: { login: 'github-actions[bot]', type: 'Bot' },
    },
  ];
  const { api, calls } = fakeGitHub(issues);

  const result = await reconcileRollingIssue({
    github: api,
    context,
    key: 'nightly-python',
    label: 'nightly-failure',
    title: 'Nightly full Python suite failed',
    active: true,
    body: 'latest',
    labels: ['automated', 'action-needed'],
  });

  assert.equal(result.updated, true);
  assert.equal(result.issueNumber, 10);
  assert.deepEqual(result.closed, [11]);
  assert.equal(calls.update[0].issue_number, 10);
  assert.equal(calls.update[1].issue_number, 11);
  assert.equal(calls.update[1].state, 'closed');
});

test('clean reconciliation closes bot legacy issues but preserves human issues', async () => {
  const issues = [
    {
      number: 20,
      title: 'Repo Health Report - 2026-10-26',
      body: 'legacy',
      user: { login: 'github-actions[bot]', type: 'Bot' },
    },
    {
      number: 21,
      title: 'Repo Health Report - please investigate',
      body: 'human report',
      user: { login: 'maintainer', type: 'User' },
    },
  ];
  const { api, calls } = fakeGitHub(issues);

  const result = await reconcileRollingIssue({
    github: api,
    context,
    key: 'repo-health',
    label: 'repo-health',
    title: 'Repo Health - action required',
    active: false,
    legacyTitlePrefixes: ['Repo Health Report -'],
  });

  assert.deepEqual(result.closed, [20]);
  assert.deepEqual(calls.update.map((call) => call.issue_number), [20]);
  assert.equal(isManagedIssue(issues[1], 'repo-health', ['Repo Health Report -']), false);
});

test('triage ignores bot issues and does not classify from long body keywords', () => {
  assert.deepEqual(
    classifyIssue({
      title: 'Security Scan - rolling',
      author: { login: 'github-actions[bot]', type: 'Bot' },
    }),
    [],
  );
  assert.deepEqual(
    classifyIssue({
      title: 'Deployment readiness mission board',
      body: 'bug docs feature security crypto tokenizer pricing',
      author: { login: 'maintainer', type: 'User' },
    }),
    [],
  );
});

test('triage adds one high-confidence type and security labels only from titles', () => {
  assert.deepEqual(
    classifyIssue({
      title: 'Free calculator - would you add this?',
      author: { login: 'contributor', type: 'User' },
    }),
    ['question'],
  );
  assert.deepEqual(
    classifyIssue({
      title: 'CVE-2026-12345 security advisory',
      labels: [{ name: 'bug' }],
      author: { login: 'researcher', type: 'User' },
    }),
    ['security', 'priority-high'],
  );
});
