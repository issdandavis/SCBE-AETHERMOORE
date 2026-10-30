'use strict';

const MARKER_PREFIX = 'scbe-automation';

function automationMarker(key) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(key)) {
    throw new Error(`Invalid automation key: ${key}`);
  }
  return `<!-- ${MARKER_PREFIX}:${key} -->`;
}

function isGitHubActionsBot(user = {}) {
  const login = String(user.login || '').toLowerCase();
  return (
    user.type === 'Bot' ||
    login === 'github-actions[bot]' ||
    login === 'app/github-actions'
  );
}

function isManagedIssue(issue, key, legacyTitlePrefixes = []) {
  const marker = automationMarker(key);
  if (String(issue.body || '').includes(marker)) {
    return true;
  }

  return (
    isGitHubActionsBot(issue.user) &&
    legacyTitlePrefixes.some((prefix) => String(issue.title || '').startsWith(prefix))
  );
}

async function listOpenIssues(github, context, label) {
  const request = {
    owner: context.repo.owner,
    repo: context.repo.repo,
    state: 'open',
    labels: label,
    per_page: 100,
  };

  if (typeof github.paginate === 'function') {
    return github.paginate(github.rest.issues.listForRepo, request);
  }

  const response = await github.rest.issues.listForRepo(request);
  return response.data;
}

function normalizedLabels(primaryLabel, labels) {
  return [...new Set([primaryLabel, ...labels].filter(Boolean))];
}

async function closeIssue(github, context, issue) {
  await github.rest.issues.update({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: issue.number,
    state: 'closed',
    state_reason: 'completed',
  });
}

/**
 * Reconcile one automation-owned issue.
 *
 * Human-authored issues are never closed merely because they share a label or
 * title. Legacy issues are adopted only when GitHub Actions authored them and
 * their title matches an explicit prefix.
 */
async function reconcileRollingIssue({
  github,
  context,
  key,
  label,
  title,
  active,
  body = '',
  labels = [],
  legacyTitlePrefixes = [],
}) {
  if (!github || !context || !label || !title || typeof active !== 'boolean') {
    throw new Error('reconcileRollingIssue requires github, context, label, title, and active');
  }

  const marker = automationMarker(key);
  const issues = await listOpenIssues(github, context, label);
  const managed = issues.filter((issue) =>
    isManagedIssue(issue, key, legacyTitlePrefixes),
  );
  const current = managed.find((issue) => issue.title === title);
  const result = { created: false, updated: false, closed: [], issueNumber: null };

  if (!active) {
    for (const issue of managed) {
      await closeIssue(github, context, issue);
      result.closed.push(issue.number);
    }
    return result;
  }

  const managedBody = String(body).includes(marker) ? String(body) : `${marker}\n${body}`;
  const issueLabels = normalizedLabels(label, labels);

  if (current) {
    await github.rest.issues.update({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: current.number,
      title,
      body: managedBody,
      labels: issueLabels,
      state: 'open',
    });
    result.updated = true;
    result.issueNumber = current.number;
  } else {
    const response = await github.rest.issues.create({
      owner: context.repo.owner,
      repo: context.repo.repo,
      title,
      body: managedBody,
      labels: issueLabels,
    });
    result.created = true;
    result.issueNumber = response.data.number;
  }

  for (const issue of managed) {
    if (issue.number === result.issueNumber) {
      continue;
    }
    await closeIssue(github, context, issue);
    result.closed.push(issue.number);
  }

  return result;
}

module.exports = {
  automationMarker,
  isGitHubActionsBot,
  isManagedIssue,
  reconcileRollingIssue,
};
