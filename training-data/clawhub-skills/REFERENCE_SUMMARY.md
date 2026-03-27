# ClawHub Skills Reference Summary

Pulled 2026-03-26 from ClawHub for Copilot-replacement research.

---

## 1. code-review

**Source**: `code-review/SKILL.md`
**Category**: testing | **Model**: reasoning

### What It Does
Provides a structured, multi-pass code review checklist organized by dimension (Security, Performance, Correctness, Maintainability, Testing, Accessibility, Documentation) with priority levels.

### Key Patterns and Techniques
- **Three-pass review process**: (1) high-level structure scan, (2) line-by-line detail, (3) edge-case hardening. Each pass has a defined time budget and focus area.
- **Severity classification system**: Every comment is prefixed with `[CRITICAL]`, `[MAJOR]`, `[MINOR]`, or `[NIT]` -- only CRITICAL and MAJOR block merge. This eliminates ambiguity about what matters.
- **Dimension-based checklists**: Each review dimension (security, performance, etc.) has a concrete checklist of items. This turns subjective review into systematic verification.
- **Anti-pattern catalog**: Explicitly lists what NOT to do (rubber-stamping, bikeshedding, gatekeeping, scope creep reviews). Useful for training a model to avoid bad review behaviors.
- **Feedback format**: Every comment must explain WHY, suggest a FIX, and use severity labels. Good/bad example pairs for training.

### Copilot-Replacement Value
- The severity system and three-pass structure can be encoded as a review pipeline stage.
- The checklists provide concrete grounding for a review agent -- instead of vague "review this code," each dimension is a discrete evaluation pass.
- The anti-pattern list is training-signal gold: it defines the boundary between helpful and harmful review behavior.

---

## 2. security-auditor

**Source**: `security-auditor/SKILL.md`
**Category**: specialist/review | **Version**: 1.0.0

### What It Does
Comprehensive security audit framework based on OWASP Top 10, with code examples in TypeScript/Next.js, structured report format, and protected-file awareness.

### Key Patterns and Techniques
- **OWASP Top 10 mapped to code patterns**: Each vulnerability class (A01 Broken Access Control, A02 Cryptographic Failures, A03 Injection, A07 XSS, A05 Misconfiguration) has paired BAD/GOOD code examples. This is directly usable as SFT training pairs.
- **Trigger-based activation**: Uses a `triggers` list in frontmatter (security, vulnerability, OWASP, XSS, CSRF, etc.) to determine when to activate. This is the skill-routing pattern -- match user intent to specialist skill.
- **Security headers template**: Complete copy-paste security header config for Next.js. Practical, production-ready output.
- **Input validation patterns**: Zod schemas for API validation, file upload magic-byte validation. Shows defense-in-depth from schema to binary level.
- **Authentication stack**: JWT creation/verification with jose, cookie security settings (httpOnly, secure, sameSite), rate limiting with Upstash.
- **Structured audit report format**: Findings categorized as Critical/High/Medium/Low with OWASP reference, file location, fix, and risk description.
- **Protected file patterns**: Lists sensitive files (.env, auth.ts, middleware.ts, prisma schema, package.json) that need extra scrutiny.

### Copilot-Replacement Value
- The BAD/GOOD code pair pattern is the most directly useful thing here for building a code assistant. Each pair is a natural SFT example.
- The trigger/routing pattern shows how to build a skill-dispatch layer: when the user's context matches security keywords, route to the security specialist.
- The structured report format is a strong output template for an automated security review agent.

---

## 3. email-daily-summary

**Source**: `email-daily-summary/SKILL.md`
**Flagged**: Suspicious by VirusTotal (installed with --force)

### What It Does
Browser-automation-based email summarizer. Uses `browser-use` CLI to open real browser sessions, scrape email inboxes (Gmail, Outlook, QQ Mail, 163), and generate daily digest reports.

### Key Patterns and Techniques
- **Real browser session reuse**: `--browser real` mode reuses existing Chrome login sessions, avoiding credential storage. This is the cleanest pattern for authenticated web automation.
- **DOM scraping with eval**: Injects JavaScript via `browser-use eval` to extract structured data from email DOM elements. Uses CSS selectors specific to Gmail's DOM structure.
- **Multi-provider support table**: Maps login URLs and inbox URLs for 6 email providers. Shows the pattern of a provider-abstraction layer.
- **Cron/launchd scheduling**: Includes templates for both crontab and macOS launchd plist for daily automation.
- **AI-powered extraction**: Optional `browser-use extract` with natural-language prompts for AI-based email parsing.
- **Allowed-tools scoping**: Frontmatter restricts the skill to only `Bash(browser-use:*)`, `Bash(echo:*)`, `Bash(date:*)` -- demonstrates sandboxing.

### Copilot-Replacement Value
- The browser-session-reuse pattern is critical for any agent that needs to interact with authenticated web services without storing credentials.
- The tool-scoping via `allowed-tools` frontmatter is a governance primitive -- limits what a skill can do.
- The provider-abstraction table pattern (URL mapping per service) is reusable for any multi-platform integration skill.
- NOTE: This skill was flagged suspicious. The DOM-scraping approach is fragile and the Chinese-language documentation suggests it targets a different market. Review code carefully before incorporating patterns.

---

## 4. code-review-fix

**Source**: `code-review-fix/SKILL.md`

### What It Does
Lightweight code review + auto-fix skill with slash-command interface. Supports modes: default review, `--fix` (auto-repair), `--security` (security-only), `--explain` (educational).

### Key Patterns and Techniques
- **Mode-based invocation**: Single command with flags that change behavior (`--fix`, `--security`, `--explain`). Clean UX pattern for multi-modal skills.
- **Freemium pricing model**: First 3 uses free, then $0.001 USDT per call via skillpay.me. Shows monetization integration at the skill level.
- **Minimal footprint**: The entire SKILL.md is ~34 lines. Demonstrates that a useful skill doesn't need to be complex -- it just needs clear triggers and modes.
- **Combined detect + fix**: Unlike `code-review` which only reviews, this one can also auto-fix. The `--fix` flag pattern is the key differentiator.

### Copilot-Replacement Value
- The mode-flag pattern (`--fix`, `--security`, `--explain`) is a strong UX model for a code assistant. One entry point, multiple behaviors.
- The pricing/monetization hook shows how to build a skill marketplace. Relevant if building a commercial Copilot alternative.
- The `--explain` mode is pedagogically valuable -- a code assistant that teaches while it fixes.

---

## 5. git-workflow

**Source**: `git-workflow/SKILL.md`
**Author**: OpenClaw team | **Version**: 1.0.0

### What It Does
Git automation skill that detects changes, generates commit messages from diff content, handles multi-repo workflows, and includes troubleshooting for common failures.

### Key Patterns and Techniques
- **Four-step pipeline**: Detect changes -> Stage files -> Generate commit message -> Commit and push. Each step is a discrete, composable action.
- **Commit message generation from diffs**: Auto-generates conventional commit messages (feat/fix/docs/style/refactor/test/chore) based on what changed. This is the core Copilot-like behavior.
- **Multi-repo awareness**: Can identify which repository a file belongs to and route commits accordingly. Pattern: repo-dispatch based on file path.
- **Troubleshooting catalog**: Common Git errors (auth failure, config missing, merge conflicts) with step-by-step fixes. Useful for building an error-recovery agent.
- **Best practices encoded**: Commit frequency rules, message style guide, branch naming conventions. These are policy constraints that can be enforced programmatically.

### Copilot-Replacement Value
- The auto-generated commit message pattern is table stakes for a Copilot replacement. The conventional-commit type detection is the key algorithm.
- Multi-repo routing is an advanced feature most Copilot alternatives lack.
- The troubleshooting catalog is a natural fit for a self-healing agent: detect error -> look up fix -> apply automatically.

---

## 6. security-scanner

**Source**: `security-scanner/SKILL.md`

### What It Does
Wraps external security tools (nmap, nuclei, nikto, sslscan, testssl.sh) into a unified scanning workflow with structured report output.

### Key Patterns and Techniques
- **Tool orchestration**: Doesn't implement scanning itself -- wraps existing tools (nmap, nuclei, nikto, sslscan) with consistent invocation patterns and output formatting.
- **Scan-type taxonomy**: Quick Recon, Full Port Scan, Web Application Scan, SSL/TLS Analysis. Each is a named workflow with specific tool combinations.
- **Structured report output**: Standardized report format saved to `reports/security-scan-YYYY-MM-DD.md` with target info, open ports, vulnerabilities (severity-rated), and recommendations.
- **Ethics guardrails**: Explicit rules about authorization, written permission, responsible disclosure. This is a safety boundary encoded in the skill.
- **Minimal skill, maximum leverage**: The skill is only 67 lines but orchestrates 5+ external tools. Pattern: thin orchestration layer over powerful existing tools.

### Copilot-Replacement Value
- The tool-orchestration pattern is the most transferable lesson: a code assistant should wrap and coordinate existing tools (linters, formatters, type checkers, test runners) rather than reimplementing them.
- The scan-type taxonomy shows how to structure multi-mode operations with named presets.
- The ethics guardrails are directly applicable to any agent that interacts with external systems -- always scope what it's allowed to do.

---

## Cross-Cutting Patterns for Building a Copilot Replacement

### 1. Skill Routing via Triggers
Skills declare when they should activate using `triggers` lists or `description` fields. A Copilot replacement needs a dispatcher that matches user intent to the right specialist skill.

### 2. Severity/Priority Classification
Both review skills use severity levels to separate blocking issues from suggestions. A code assistant should always classify its output by importance.

### 3. BAD/GOOD Code Pairs
The security-auditor's pattern of showing vulnerable code alongside the fix is the ideal SFT training format. Every code suggestion should implicitly encode this before/after structure.

### 4. Mode Flags for Multi-Modal Skills
A single skill entry point with `--fix`, `--explain`, `--security` flags is cleaner than separate skills. Users remember one command, not six.

### 5. Tool Orchestration Over Reimplementation
The security-scanner wraps nmap/nuclei rather than scanning itself. A Copilot replacement should orchestrate existing dev tools (ESLint, Prettier, pytest, tsc) rather than duplicating their logic.

### 6. Structured Output Templates
Every skill produces structured output (audit reports, commit messages, email digests). Consistent output format makes downstream processing (dashboards, notifications, training data) trivial.

### 7. Governance/Safety Boundaries
Skills scope themselves via `allowed-tools`, ethics sections, and protected-file lists. A Copilot replacement needs explicit boundaries on what it can modify and what requires human approval.

### 8. Troubleshooting Catalogs
Error -> Diagnosis -> Fix mappings (from git-workflow) enable self-healing agents. When an operation fails, look up the error pattern and apply the documented fix automatically.
