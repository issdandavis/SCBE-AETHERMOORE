/**
 * @file index.js
 * @module scbe-repo-manager
 * @description Probot GitHub App for automated SCBE-AETHERMOORE repository management.
 *
 * Event handlers:
 *   - issues.opened        Auto-triage: detect component, add labels, post checklist
 *   - pull_request.opened  Auto-review: check tests, changelog, layer tags, lint status
 *   - push (main)          Auto-changelog: categorize commits, update CHANGELOG.md
 *   - check_suite.completed  Add "ready-to-merge" label when all checks pass on a PR
 *   - schedule (daily)     Stale issue/PR cleanup, dependency update reminders
 */

// ─── Component Detection ────────────────────────────────────────────────────

/**
 * Maps keywords found in issue/PR titles and bodies to SCBE component labels.
 * Order matters: first match wins, so put more specific patterns before generic ones.
 */
const COMPONENT_PATTERNS = [
  {
    label: "component:crypto",
    keywords: [
      "crypto", "pqc", "post-quantum", "kyber", "dilithium", "ml-kem",
      "ml-dsa", "aes", "envelope", "nonce", "hkdf", "spiral-seal",
      "spiralseal", "kms", "replay", "hmac",
    ],
  },
  {
    label: "component:harmonic",
    keywords: [
      "harmonic", "pipeline", "14-layer", "fourteen layer", "layer 1",
      "layer 2", "layer 3", "layer 4", "layer 5", "layer 6", "layer 7",
      "layer 8", "layer 9", "layer 10", "layer 11", "layer 12", "layer 13",
      "layer 14", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "l9",
      "l10", "l11", "l12", "l13", "l14", "poincare", "hyperbolic",
      "hamiltonian", "cfi", "mobius", "breathing",
    ],
  },
  {
    label: "component:tongues",
    keywords: [
      "tongue", "langues", "sacred tongue", "ko ", " av ", " ru ", " ca ",
      " um ", " dr ", "tokenizer", "golden ratio", "phi weight",
    ],
  },
  {
    label: "component:game",
    keywords: [
      "game", "spiralverse", "everweave", "cstm", "player", "nursery",
      "story", "lore", "choicescript", "manhwa", "polly", "kael",
      "marcus", "aethermoor",
    ],
  },
  {
    label: "component:api",
    keywords: [
      "api", "fastapi", "uvicorn", "express", "gateway", "endpoint",
      "rest", "graphql", "router", "middleware", "cors",
    ],
  },
  {
    label: "component:ci",
    keywords: [
      "ci", "cd", "workflow", "github action", "pipeline", "deploy",
      "docker", "release", "publish", "npm publish", "auto-publish",
    ],
  },
  {
    label: "component:testing",
    keywords: [
      "test", "vitest", "pytest", "property test", "fast-check",
      "hypothesis", "coverage", "fixture", "mock", "snapshot",
      "benchmark", "stress test",
    ],
  },
  {
    label: "component:docs",
    keywords: [
      "doc", "readme", "changelog", "spec", "architecture",
      "runbook", "guide", "tutorial", "patent",
    ],
  },
];

/**
 * Detect which SCBE component(s) an issue or PR relates to.
 * @param {string} title - Issue/PR title
 * @param {string} body  - Issue/PR body (may be null)
 * @returns {string[]} Array of component label strings
 */
function detectComponents(title, body) {
  const text = `${title} ${body || ""}`.toLowerCase();
  const matched = [];

  for (const { label, keywords } of COMPONENT_PATTERNS) {
    for (const kw of keywords) {
      if (text.includes(kw.toLowerCase())) {
        matched.push(label);
        break; // one match per component is enough
      }
    }
  }

  return matched;
}

// ─── Commit Classification ──────────────────────────────────────────────────

/**
 * Conventional-commit prefix to changelog section mapping.
 */
const COMMIT_CATEGORIES = {
  feat: "Added",
  fix: "Fixed",
  docs: "Documentation",
  test: "Testing",
  security: "Security",
  refactor: "Changed",
  perf: "Performance",
  chore: "Maintenance",
  ci: "CI/CD",
  build: "Build",
  style: "Style",
};

/**
 * Parse a conventional commit message into { category, scope, description }.
 * Falls back to "Maintenance" for non-conventional messages.
 * @param {string} message - Full commit message (first line)
 * @returns {{ category: string, scope: string|null, description: string }}
 */
function classifyCommit(message) {
  const match = message.match(
    /^(feat|fix|docs|test|security|refactor|perf|chore|ci|build|style)(?:\(([^)]+)\))?!?:\s*(.+)/i
  );

  if (match) {
    const prefix = match[1].toLowerCase();
    return {
      category: COMMIT_CATEGORIES[prefix] || "Maintenance",
      scope: match[2] || null,
      description: match[3].trim(),
    };
  }

  // Heuristic fallback for non-conventional messages
  const lower = message.toLowerCase();
  if (lower.includes("fix") || lower.includes("bug") || lower.includes("patch")) {
    return { category: "Fixed", scope: null, description: message };
  }
  if (lower.includes("add") || lower.includes("new") || lower.includes("feature") || lower.includes("implement")) {
    return { category: "Added", scope: null, description: message };
  }
  if (lower.includes("doc") || lower.includes("readme")) {
    return { category: "Documentation", scope: null, description: message };
  }
  if (lower.includes("test")) {
    return { category: "Testing", scope: null, description: message };
  }
  if (lower.includes("security") || lower.includes("vuln") || lower.includes("cve")) {
    return { category: "Security", scope: null, description: message };
  }

  return { category: "Maintenance", scope: null, description: message };
}

// ─── PR Review Helpers ──────────────────────────────────────────────────────

/**
 * Examine the list of changed files in a PR and produce a review checklist.
 * @param {string[]} filenames - Array of changed file paths
 * @returns {{ hasTests: boolean, hasChangelog: boolean, hasLayerTags: boolean, items: string[] }}
 */
function buildReviewChecklist(filenames) {
  const hasTests = filenames.some(
    (f) =>
      f.includes(".test.") ||
      f.includes(".spec.") ||
      f.startsWith("tests/") ||
      f.startsWith("test/") ||
      f.includes("test_")
  );

  const hasChangelog = filenames.some(
    (f) => f.toLowerCase() === "changelog.md"
  );

  // Layer tags: files under src/harmonic/, src/spectral/, src/symphonic/, or axiom_grouped/
  const hasLayerTags = filenames.some(
    (f) =>
      f.includes("src/harmonic/") ||
      f.includes("src/spectral/") ||
      f.includes("src/symphonic") ||
      f.includes("axiom_grouped/")
  );

  const touchesSrc = filenames.some(
    (f) => f.startsWith("src/") || f.endsWith(".ts") || f.endsWith(".py")
  );

  const touchesCrypto = filenames.some(
    (f) => f.includes("crypto/") || f.includes("pqc") || f.includes("seal")
  );

  const touchesConfig = filenames.some(
    (f) =>
      f.includes("package.json") ||
      f.includes("tsconfig") ||
      f.includes("pyproject") ||
      f.includes("Dockerfile") ||
      f.includes(".yml") ||
      f.includes(".yaml")
  );

  const items = [];

  // Test coverage
  if (touchesSrc && hasTests) {
    items.push("- [x] Test files included");
  } else if (touchesSrc && !hasTests) {
    items.push("- [ ] **Missing test files** — source changes should include corresponding tests");
  } else {
    items.push("- [x] No source changes requiring tests");
  }

  // Changelog
  if (hasChangelog) {
    items.push("- [x] CHANGELOG.md updated");
  } else if (touchesSrc) {
    items.push("- [ ] CHANGELOG.md not updated — consider adding an entry under `[Unreleased]`");
  }

  // Layer tags (for harmonic pipeline changes)
  if (hasLayerTags) {
    items.push("- [ ] Verify `@layer` tags in file headers match the layers touched");
  }

  // Crypto review flag
  if (touchesCrypto) {
    items.push("- [ ] **Crypto change detected** — requires security review before merge");
  }

  // Config review flag
  if (touchesConfig) {
    items.push("- [ ] Configuration file changed — verify no secrets or breaking changes");
  }

  // Standard items always included
  items.push("- [ ] Lint / format checks pass (`npm run lint` + `npm run lint:python`)");
  items.push("- [ ] TypeScript builds cleanly (`npm run build`)");

  return { hasTests, hasChangelog, hasLayerTags, items };
}

// ─── Changelog Builder ──────────────────────────────────────────────────────

/**
 * Build a changelog patch from an array of classified commits.
 * @param {{ category: string, scope: string|null, description: string, sha: string }[]} classified
 * @returns {string} Markdown block to insert into CHANGELOG.md
 */
function buildChangelogPatch(classified) {
  // Group by category
  const groups = {};
  for (const c of classified) {
    if (!groups[c.category]) groups[c.category] = [];
    const scopeTag = c.scope ? `**${c.scope}**: ` : "";
    groups[c.category].push(`- ${scopeTag}${c.description} (${c.sha.slice(0, 7)})`);
  }

  // Desired section order
  const order = [
    "Added", "Fixed", "Changed", "Security", "Performance",
    "Documentation", "Testing", "CI/CD", "Build", "Style", "Maintenance",
  ];

  const sections = [];
  for (const cat of order) {
    if (groups[cat] && groups[cat].length > 0) {
      sections.push(`### ${cat}\n${groups[cat].join("\n")}`);
    }
  }

  return sections.join("\n\n");
}

// ─── Main Probot App ────────────────────────────────────────────────────────

/**
 * @param {import('probot').Probot} app
 */
export default (app) => {
  app.log.info("SCBE Repo Manager loaded");

  // ── 1. Issue Triage ─────────────────────────────────────────────────────
  app.on("issues.opened", async (context) => {
    const { title, body, number } = context.payload.issue;
    const owner = context.payload.repository.owner.login;
    const repo = context.payload.repository.name;

    app.log.info(`Issue #${number} opened: ${title}`);

    // Detect components
    const componentLabels = detectComponents(title, body);

    // Detect issue type from title conventions
    const typeLabels = [];
    const lower = (title + " " + (body || "")).toLowerCase();
    if (lower.includes("bug") || lower.includes("error") || lower.includes("crash") || lower.includes("broken")) {
      typeLabels.push("bug");
    }
    if (lower.includes("feature") || lower.includes("request") || lower.includes("enhancement") || lower.includes("proposal")) {
      typeLabels.push("enhancement");
    }
    if (lower.includes("question") || lower.includes("help") || lower.includes("how to")) {
      typeLabels.push("question");
    }
    if (lower.includes("security") || lower.includes("vulnerability") || lower.includes("cve")) {
      typeLabels.push("security");
    }

    // Priority detection
    if (lower.includes("urgent") || lower.includes("critical") || lower.includes("p0") || lower.includes("blocker")) {
      typeLabels.push("priority:critical");
    } else if (lower.includes("important") || lower.includes("p1") || lower.includes("high priority")) {
      typeLabels.push("priority:high");
    }

    const allLabels = [...componentLabels, ...typeLabels];

    // If no component detected, add "needs-triage"
    if (componentLabels.length === 0) {
      allLabels.push("needs-triage");
    }

    // Add labels (create them if they do not exist)
    if (allLabels.length > 0) {
      // Ensure labels exist in the repo
      for (const label of allLabels) {
        try {
          await context.octokit.issues.getLabel({ owner, repo, name: label });
        } catch {
          // Label does not exist — create it
          const colorMap = {
            "component:crypto": "d4c5f9",
            "component:harmonic": "0075ca",
            "component:tongues": "e4e669",
            "component:game": "f9d0c4",
            "component:api": "1d76db",
            "component:ci": "bfdadc",
            "component:testing": "c2e0c6",
            "component:docs": "0e8a16",
            "needs-triage": "fbca04",
            "bug": "d73a4a",
            "enhancement": "a2eeef",
            "question": "d876e3",
            "security": "b60205",
            "priority:critical": "b60205",
            "priority:high": "ff9f1c",
          };
          await context.octokit.issues.createLabel({
            owner,
            repo,
            name: label,
            color: colorMap[label] || "ededed",
            description: `Auto-created by SCBE Repo Manager`,
          });
        }
      }

      await context.octokit.issues.addLabels(
        context.issue({ labels: allLabels })
      );
    }

    // Post a triage summary comment
    const componentList =
      componentLabels.length > 0
        ? componentLabels.map((l) => `\`${l}\``).join(", ")
        : "_No component detected — marked as `needs-triage`_";

    const triageComment = [
      `## Auto-Triage Summary`,
      "",
      `**Components detected**: ${componentList}`,
      typeLabels.length > 0
        ? `**Type**: ${typeLabels.map((l) => `\`${l}\``).join(", ")}`
        : "",
      "",
      "---",
      "_Triaged automatically by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
    ]
      .filter(Boolean)
      .join("\n");

    await context.octokit.issues.createComment(
      context.issue({ body: triageComment })
    );

    app.log.info(`Issue #${number} triaged with labels: ${allLabels.join(", ")}`);
  });

  // ── 2. Pull Request Review Checklist ────────────────────────────────────
  app.on("pull_request.opened", async (context) => {
    const pr = context.payload.pull_request;
    const owner = context.payload.repository.owner.login;
    const repo = context.payload.repository.name;

    app.log.info(`PR #${pr.number} opened: ${pr.title}`);

    // Fetch the list of changed files
    const { data: files } = await context.octokit.pulls.listFiles({
      owner,
      repo,
      pull_number: pr.number,
      per_page: 300,
    });

    const filenames = files.map((f) => f.filename);
    const checklist = buildReviewChecklist(filenames);

    // Detect components for labeling
    const componentLabels = detectComponents(pr.title, pr.body);

    // Add component labels to the PR
    if (componentLabels.length > 0) {
      // Ensure labels exist
      for (const label of componentLabels) {
        try {
          await context.octokit.issues.getLabel({ owner, repo, name: label });
        } catch {
          const colorMap = {
            "component:crypto": "d4c5f9",
            "component:harmonic": "0075ca",
            "component:tongues": "e4e669",
            "component:game": "f9d0c4",
            "component:api": "1d76db",
            "component:ci": "bfdadc",
            "component:testing": "c2e0c6",
            "component:docs": "0e8a16",
          };
          await context.octokit.issues.createLabel({
            owner,
            repo,
            name: label,
            color: colorMap[label] || "ededed",
            description: `Auto-created by SCBE Repo Manager`,
          });
        }
      }

      await context.octokit.issues.addLabels({
        owner,
        repo,
        issue_number: pr.number,
        labels: componentLabels,
      });
    }

    // Size label based on total lines changed
    const totalChanges = files.reduce((sum, f) => sum + f.additions + f.deletions, 0);
    let sizeLabel = "size:S";
    if (totalChanges > 1000) sizeLabel = "size:XL";
    else if (totalChanges > 500) sizeLabel = "size:L";
    else if (totalChanges > 100) sizeLabel = "size:M";

    try {
      await context.octokit.issues.getLabel({ owner, repo, name: sizeLabel });
    } catch {
      const sizeColors = { "size:S": "69db7c", "size:M": "ffd33d", "size:L": "ff9f1c", "size:XL": "d73a4a" };
      await context.octokit.issues.createLabel({
        owner,
        repo,
        name: sizeLabel,
        color: sizeColors[sizeLabel] || "ededed",
        description: "PR size classification",
      });
    }
    await context.octokit.issues.addLabels({
      owner,
      repo,
      issue_number: pr.number,
      labels: [sizeLabel],
    });

    // File summary
    const fileGroups = {
      typescript: filenames.filter((f) => f.endsWith(".ts") || f.endsWith(".tsx")).length,
      python: filenames.filter((f) => f.endsWith(".py")).length,
      config: filenames.filter((f) => f.endsWith(".json") || f.endsWith(".yml") || f.endsWith(".yaml") || f.endsWith(".toml")).length,
      docs: filenames.filter((f) => f.endsWith(".md")).length,
      other: 0,
    };
    fileGroups.other = filenames.length - fileGroups.typescript - fileGroups.python - fileGroups.config - fileGroups.docs;

    const fileSummaryParts = [];
    if (fileGroups.typescript > 0) fileSummaryParts.push(`${fileGroups.typescript} TypeScript`);
    if (fileGroups.python > 0) fileSummaryParts.push(`${fileGroups.python} Python`);
    if (fileGroups.config > 0) fileSummaryParts.push(`${fileGroups.config} config`);
    if (fileGroups.docs > 0) fileSummaryParts.push(`${fileGroups.docs} docs`);
    if (fileGroups.other > 0) fileSummaryParts.push(`${fileGroups.other} other`);

    // Post the review checklist comment
    const reviewBody = [
      `## PR Review Checklist`,
      "",
      `**${filenames.length} files changed** (${fileSummaryParts.join(", ")}) — **+${files.reduce((s, f) => s + f.additions, 0)} / -${files.reduce((s, f) => s + f.deletions, 0)}** lines — \`${sizeLabel}\``,
      "",
      ...checklist.items,
      "",
      "---",
      "",
      "<details>",
      "<summary>Changed files</summary>",
      "",
      ...filenames.map((f) => `- \`${f}\``),
      "",
      "</details>",
      "",
      "_Review checklist generated by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
    ].join("\n");

    await context.octokit.issues.createComment({
      owner,
      repo,
      issue_number: pr.number,
      body: reviewBody,
    });

    app.log.info(`PR #${pr.number} review checklist posted (${filenames.length} files, ${sizeLabel})`);
  });

  // ── 3. Auto-Changelog on Push to Main ───────────────────────────────────
  app.on("push", async (context) => {
    const { ref, commits, repository } = context.payload;
    const owner = repository.owner.login || repository.owner.name;
    const repo = repository.name;
    const defaultBranch = repository.default_branch || "main";

    // Only act on pushes to the default branch
    if (ref !== `refs/heads/${defaultBranch}`) return;

    // Skip if no commits (e.g., branch deletion)
    if (!commits || commits.length === 0) return;

    app.log.info(`Push to ${defaultBranch}: ${commits.length} commit(s)`);

    // Filter out merge commits and bot commits
    const meaningfulCommits = commits.filter((c) => {
      if (c.message.startsWith("Merge ")) return false;
      if (c.author && c.author.username === "scbe-repo-manager[bot]") return false;
      return true;
    });

    if (meaningfulCommits.length === 0) {
      app.log.info("No meaningful commits to changelog");
      return;
    }

    // Classify each commit
    const classified = meaningfulCommits.map((c) => ({
      ...classifyCommit(c.message.split("\n")[0]),
      sha: c.id,
    }));

    // Build the changelog patch
    const patch = buildChangelogPatch(classified);
    if (!patch) return;

    // Fetch current CHANGELOG.md
    let currentContent = "";
    let currentSha = null;

    try {
      const { data: file } = await context.octokit.repos.getContent({
        owner,
        repo,
        path: "CHANGELOG.md",
        ref: defaultBranch,
      });
      currentContent = Buffer.from(file.content, "base64").toString("utf-8");
      currentSha = file.sha;
    } catch (err) {
      if (err.status === 404) {
        // No CHANGELOG.md yet — create one
        currentContent = "# SCBE Production Pack Changelog\n\n## [Unreleased]\n";
        currentSha = null;
      } else {
        throw err;
      }
    }

    // Insert the patch under the [Unreleased] heading
    const today = new Date().toISOString().slice(0, 10);
    const insertMarker = "## [Unreleased]";
    const markerIndex = currentContent.indexOf(insertMarker);

    let updatedContent;
    if (markerIndex !== -1) {
      const afterMarker = markerIndex + insertMarker.length;
      // Find the next section heading or end of file
      const nextSection = currentContent.indexOf("\n## ", afterMarker);
      const insertionPoint = nextSection !== -1 ? nextSection : currentContent.length;

      // Check if there is already content under [Unreleased]
      const existingUnreleased = currentContent.slice(afterMarker, insertionPoint).trim();

      if (existingUnreleased) {
        // Append to existing unreleased section
        updatedContent =
          currentContent.slice(0, insertionPoint) +
          "\n\n" +
          `<!-- auto-changelog ${today} -->\n` +
          patch +
          "\n" +
          currentContent.slice(insertionPoint);
      } else {
        // Empty unreleased section — add content
        updatedContent =
          currentContent.slice(0, afterMarker) +
          "\n\n" +
          `<!-- auto-changelog ${today} -->\n` +
          patch +
          "\n" +
          currentContent.slice(insertionPoint);
      }
    } else {
      // No [Unreleased] heading — prepend one
      updatedContent =
        `# SCBE Production Pack Changelog\n\n## [Unreleased]\n\n` +
        `<!-- auto-changelog ${today} -->\n` +
        patch +
        "\n\n" +
        currentContent;
    }

    // Commit the updated CHANGELOG.md
    const commitMessage = `docs(changelog): auto-update from ${meaningfulCommits.length} commit(s) [skip ci]`;

    const updateParams = {
      owner,
      repo,
      path: "CHANGELOG.md",
      message: commitMessage,
      content: Buffer.from(updatedContent, "utf-8").toString("base64"),
      branch: defaultBranch,
    };

    if (currentSha) {
      updateParams.sha = currentSha;
    }

    await context.octokit.repos.createOrUpdateFileContents(updateParams);

    app.log.info(`CHANGELOG.md updated with ${classified.length} entries`);
  });

  // ── 4. Ready-to-Merge on Check Suite Pass ───────────────────────────────
  app.on("check_suite.completed", async (context) => {
    const { check_suite: suite, repository } = context.payload;
    const owner = repository.owner.login;
    const repo = repository.name;

    // Only interested in successful check suites
    if (suite.conclusion !== "success") return;

    // Find associated pull requests
    const pullRequests = suite.pull_requests || [];
    if (pullRequests.length === 0) return;

    const readyLabel = "ready-to-merge";

    // Ensure the label exists
    try {
      await context.octokit.issues.getLabel({ owner, repo, name: readyLabel });
    } catch {
      await context.octokit.issues.createLabel({
        owner,
        repo,
        name: readyLabel,
        color: "0e8a16",
        description: "All CI checks passed — safe to merge",
      });
    }

    for (const pr of pullRequests) {
      // Verify ALL check suites for this PR head SHA have passed
      const { data: checkSuites } = await context.octokit.checks.listSuitesForRef({
        owner,
        repo,
        ref: suite.head_sha,
      });

      const allPassed = checkSuites.check_suites.every(
        (cs) =>
          cs.conclusion === "success" ||
          cs.conclusion === "neutral" ||
          cs.conclusion === "skipped" ||
          cs.status !== "completed" // still running — do not block
      );

      const anyFailed = checkSuites.check_suites.some(
        (cs) => cs.status === "completed" && cs.conclusion === "failure"
      );

      if (anyFailed) {
        // Remove the label if it was previously applied
        try {
          await context.octokit.issues.removeLabel({
            owner,
            repo,
            issue_number: pr.number,
            name: readyLabel,
          });
        } catch {
          // Label was not there — that is fine
        }
        continue;
      }

      // All completed suites passed (or some are still running)
      const allCompleted = checkSuites.check_suites.every(
        (cs) => cs.status === "completed"
      );

      if (allPassed && allCompleted) {
        // Fetch current labels to avoid duplicate
        const { data: currentLabels } = await context.octokit.issues.listLabelsOnIssue({
          owner,
          repo,
          issue_number: pr.number,
        });

        const alreadyHas = currentLabels.some((l) => l.name === readyLabel);
        if (!alreadyHas) {
          await context.octokit.issues.addLabels({
            owner,
            repo,
            issue_number: pr.number,
            labels: [readyLabel],
          });
          app.log.info(`PR #${pr.number} marked as ready-to-merge`);
        }
      }
    }
  });

  // ── 5. Scheduled: Stale Cleanup & Dependency Reminders ──────────────────
  //
  // Probot does not have native cron. Use one of:
  //   a) probot-scheduler (npm package)
  //   b) GitHub Actions cron that triggers a repository_dispatch
  //   c) External cron hitting the webhook URL
  //
  // This handler listens for `repository_dispatch` with type "scheduled-maintenance"
  // so you can trigger it from a GitHub Actions cron workflow or external scheduler.
  //
  //   Example GitHub Action trigger:
  //     - cron: '0 8 * * *'
  //     steps:
  //       - uses: peter-evans/repository-dispatch@v3
  //         with:
  //           event-type: scheduled-maintenance
  //
  app.on("repository_dispatch", async (context) => {
    if (context.payload.action !== "scheduled-maintenance") return;

    const owner = context.payload.repository.owner.login;
    const repo = context.payload.repository.name;
    const staleDays = parseInt(process.env.STALE_DAYS || "30", 10);
    const staleDate = new Date();
    staleDate.setDate(staleDate.getDate() - staleDays);
    const staleDateISO = staleDate.toISOString().slice(0, 10);

    app.log.info(`Running scheduled maintenance (stale threshold: ${staleDays} days)`);

    // ── Stale Issues ──────────────────────────────────────────────────────
    const staleLabel = "stale";

    // Ensure stale label exists
    try {
      await context.octokit.issues.getLabel({ owner, repo, name: staleLabel });
    } catch {
      await context.octokit.issues.createLabel({
        owner,
        repo,
        name: staleLabel,
        color: "ededed",
        description: "Inactive for 30+ days — will be closed if no activity",
      });
    }

    // Find issues not updated since the threshold
    const { data: staleIssues } = await context.octokit.issues.listForRepo({
      owner,
      repo,
      state: "open",
      sort: "updated",
      direction: "asc",
      per_page: 50,
      since: "2020-01-01T00:00:00Z", // broad range to get old issues
    });

    let staleCount = 0;
    for (const issue of staleIssues) {
      // Skip pull requests (they show up in the issues endpoint)
      if (issue.pull_request) continue;

      const lastUpdated = new Date(issue.updated_at);
      if (lastUpdated >= staleDate) continue;

      // Skip issues that already have the stale label
      const hasStale = issue.labels.some((l) => l.name === staleLabel);

      // Skip issues with priority labels (do not auto-stale critical items)
      const hasPriority = issue.labels.some(
        (l) => l.name.startsWith("priority:") || l.name === "security"
      );
      if (hasPriority) continue;

      if (!hasStale) {
        // First time marking as stale — add label and comment
        await context.octokit.issues.addLabels({
          owner,
          repo,
          issue_number: issue.number,
          labels: [staleLabel],
        });

        await context.octokit.issues.createComment({
          owner,
          repo,
          issue_number: issue.number,
          body: [
            `This issue has been automatically marked as **stale** because it has not had activity in ${staleDays} days.`,
            "",
            "It will be closed in 7 days if no further activity occurs.",
            "",
            "If this issue is still relevant, please comment or remove the `stale` label.",
            "",
            "_Maintained by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
          ].join("\n"),
        });

        staleCount++;
      } else {
        // Already stale — check if it has been stale for 7+ days with no activity
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        if (lastUpdated < sevenDaysAgo) {
          await context.octokit.issues.update({
            owner,
            repo,
            issue_number: issue.number,
            state: "closed",
            state_reason: "not_planned",
          });

          await context.octokit.issues.createComment({
            owner,
            repo,
            issue_number: issue.number,
            body: [
              "Closing this issue due to inactivity.",
              "",
              "If this is still needed, feel free to reopen it.",
              "",
              "_Maintained by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
            ].join("\n"),
          });
        }
      }
    }

    // ── Stale Pull Requests ───────────────────────────────────────────────
    const { data: stalePRs } = await context.octokit.pulls.list({
      owner,
      repo,
      state: "open",
      sort: "updated",
      direction: "asc",
      per_page: 30,
    });

    let stalePRCount = 0;
    for (const pr of stalePRs) {
      const lastUpdated = new Date(pr.updated_at);
      if (lastUpdated >= staleDate) continue;

      const { data: prLabels } = await context.octokit.issues.listLabelsOnIssue({
        owner,
        repo,
        issue_number: pr.number,
      });

      const hasStale = prLabels.some((l) => l.name === staleLabel);
      if (!hasStale) {
        await context.octokit.issues.addLabels({
          owner,
          repo,
          issue_number: pr.number,
          labels: [staleLabel],
        });

        await context.octokit.issues.createComment({
          owner,
          repo,
          issue_number: pr.number,
          body: [
            `This pull request has been automatically marked as **stale** because it has not had activity in ${staleDays} days.`,
            "",
            "Please update or close this PR if it is no longer needed.",
            "",
            "_Maintained by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
          ].join("\n"),
        });

        stalePRCount++;
      }
    }

    // ── Dependency Update Reminder ────────────────────────────────────────
    // Check if package.json or requirements.txt was updated in the last 30 days
    try {
      const { data: recentCommits } = await context.octokit.repos.listCommits({
        owner,
        repo,
        per_page: 100,
        since: staleDateISO + "T00:00:00Z",
      });

      const depFilesUpdated = recentCommits.some((c) =>
        c.commit.message.includes("package") ||
        c.commit.message.includes("requirements") ||
        c.commit.message.includes("dependab") ||
        c.commit.message.includes("deps")
      );

      if (!depFilesUpdated) {
        // Check if there is already an open dependency reminder issue
        const { data: existingIssues } = await context.octokit.issues.listForRepo({
          owner,
          repo,
          state: "open",
          labels: "dependencies",
          per_page: 5,
        });

        const hasReminder = existingIssues.some((i) =>
          i.title.includes("Dependency Update Reminder")
        );

        if (!hasReminder) {
          await context.octokit.issues.create({
            owner,
            repo,
            title: `Dependency Update Reminder — ${new Date().toISOString().slice(0, 10)}`,
            body: [
              "No dependency updates detected in the last 30 days.",
              "",
              "Please review and update:",
              "- [ ] `npm outdated` — check for stale Node.js packages",
              "- [ ] `pip list --outdated` — check for stale Python packages",
              "- [ ] Review `package-lock.json` for security advisories",
              "- [ ] Run `npm audit` and `pip-audit`",
              "",
              "_Created by [SCBE Repo Manager](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/apps/scbe-github-app)._",
            ].join("\n"),
            labels: ["dependencies", "maintenance"],
          });
        }
      }
    } catch (err) {
      app.log.warn("Dependency check skipped:", err.message);
    }

    app.log.info(
      `Scheduled maintenance complete: ${staleCount} issues marked stale, ${stalePRCount} PRs marked stale`
    );
  });

  // ── Global Error Handler ────────────────────────────────────────────────
  app.onError(async (error) => {
    app.log.error("Unhandled error in SCBE Repo Manager:", error);
  });
};
