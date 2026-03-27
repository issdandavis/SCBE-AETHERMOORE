# Repository Guidelines

## Project Structure & Module Organization
- Core TypeScript code lives in `src/` (governance pipeline, crypto, agentic components).
- Python modules and runtime services are in `python/`, `api/`, and `agents/`.
- Tests are split between `tests/` (Python + integration) and TS unit tests run by Vitest.
- Documentation and architecture notes are in `docs/`.
- Deployment/runtime assets are in `deploy/`, `k8s/`, `docker`-related scripts in `scripts/`, and generated artifacts in `dist/`, `artifacts/`, and `training-data/`.

## Build, Test, and Development Commands
- `npm run build`: cleans and compiles TypeScript (`dist/`).
- `npm run typecheck`: strict TS type check without emit.
- `npm test`: runs Vitest suite.
- `npm run test:python`: runs `pytest tests/ -v`.
- `npm run test:all`: runs TS + Python tests.
- `npm run lint` / `npm run format`: Prettier checks/fixes for TS.
- `npm run lint:python` / `npm run format:python`: Flake8 and Black for Python.
- `npm run docker:build` and `npm run docker:compose`: local container workflow.

## Coding Style & Naming Conventions
- TypeScript: 2-space indentation, `camelCase` variables/functions, `PascalCase` classes/types, explicit exported types on public APIs.
- Python: Black formatting, snake_case for functions/modules, PascalCase classes.
- Keep modules scoped by domain (`crypto`, `agentic`, `harmonic`, `m4mesh`) and avoid cross-layer side effects.

## Testing Guidelines
- Add/modify tests with every behavior change.
- TS tests: colocate by feature or under `tests/` using `*.test.ts`.
- Python tests: `tests/**/test_*.py` naming.
- For security/interop changes, include at least one deterministic regression test and one boundary/invalid-input test.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
- Keep PRs scoped; include purpose, changed paths, test evidence, and rollback notes.
- Link issues/tasks and attach screenshots only for UI changes.
- Do not commit secrets, generated caches (`.pytest_cache`, `.hypothesis`, local logs), or machine-specific config.

## Security & Configuration Tips
- Keep secrets in environment variables; never hardcode keys/tokens.
- Validate all external inputs at boundaries (API, MCP tools, dataset ingest).
- Prefer deterministic outputs for governance/audit paths and log decision-relevant metadata.
- `src/` is the main codebase. Key areas: `src/harmonic/` (14-layer pipeline), `src/crypto/`, `src/api/`, `src/agentic/`, and `src/symphonic_cipher/`.
- `tests/` contains Python and TS-aligned validation suites (unit, integration, adversarial, interop).
- `scripts/` contains operational tooling (dataset generation/merge, Docker and MCP helpers).
- `training-data/` stores JSONL corpora and schemas used for SFT pipelines.
- Treat `artifacts/`, `training/runs/`, and local DB/cache files as generated outputs; avoid committing them unless required.

## Build, Test, and Development Commands
- `npm run build` — clean and compile TypeScript to `dist/`.
- `npm run typecheck` — TS static checks without emitting files.
- `npm test` — run Vitest suite.
- `npm run test:python` — run Python tests (`pytest tests/ -v`).
- `npm run test:all` — run TS + Python suites.
- `npm run lint` and `npm run lint:python` — Prettier and flake8 checks.
- `npm run format` and `npm run format:python` — TS and Python formatting.
- Docker/MCP ops: `npm run docker:doctor:api`, `npm run mcp:doctor`.

## Coding Style & Naming Conventions
- TypeScript: strict typing, small focused modules, `camelCase` for vars/functions, `PascalCase` for classes/types.
- Python: PEP 8 with type hints and docstrings; Black formatting (120-char line limit).
- Test files: Python `test_*.py`; TS `*.test.ts`.
- Prefer explicit metadata fields (`track`, `source_type`, `quality`) in training records.

## Testing Guidelines
- Frameworks: Vitest (TS), pytest + Hypothesis (Python).
- Add regression tests for every bug fix (code and math behavior).
- Run targeted tests for changed modules first, then `npm run test:all`.
- Do not increase pre-existing failure counts.

## Commit & Pull Request Guidelines
- Use Conventional Commits with scope, e.g. `feat(training): ...`, `fix(physics): ...`, `chore(docker): ...`.
- PRs should include:
  - concise summary of behavior changes,
  - affected paths/modules,
  - test evidence (commands + results),
  - linked issue(s) when applicable.
- Keep PRs focused; avoid unrelated generated artifacts or secrets.

## Security & Configuration Tips
- Never commit API tokens or secrets; use `.env.example` as template.
- Prefer script-based ops (`scripts/scbe_docker_status.ps1`, `scripts/scbe_mcp_terminal.ps1`) for reproducible local control.

## Apollo Data Collection Pipeline

Apollo is the email/content triage and training data agent. Any agent (Claude, Codex, Gemini) can run these commands.

### Email Check
```bash
# Check ProtonMail + Gmail for important emails (patent, revenue, outreach)
python scripts/system/daily_patent_check.py --check-email

# Full Apollo email scan with tongue classification
python scripts/apollo/email_reader.py --days 3 --route

# Interactive search
python scripts/apollo/apollo_core.py search "patent" --days 30

# Teach Apollo (correct a classification)
python scripts/apollo/apollo_core.py teach <msg_id> --correct-tongue RU --correct-route commitments

# Collect + scrub secrets + generate SFT
python scripts/apollo/apollo_core.py collect --days 7
```

### YouTube Transcript Collection
```bash
# List curated channels
python scripts/apollo/youtube_transcript_collector.py channels

# Collect from one channel
python scripts/apollo/youtube_transcript_collector.py collect --channel "3Blue1Brown" --max 5

# Collect from all curated channels
python scripts/apollo/youtube_transcript_collector.py collect-all --max-per-channel 3

# Show collection stats
python scripts/apollo/youtube_transcript_collector.py stats
```

Transcript API is free (youtube-transcript-api). No API key needed for public videos.
Curated channels are in `config/training/curated_youtube_channels.json`.

### Dark Web Sweeper (requires Tor)
```bash
# Check Tor connection
python scripts/apollo/tor_sweeper.py check

# Sweep trusted onion sites (dry-run if Tor not running)
python scripts/apollo/tor_sweeper.py sweep

# Sweep specific tier only
python scripts/apollo/tor_sweeper.py sweep --tier NEWS_AND_JOURNALISM
```

Trusted sites registry: `config/security/trusted_onion_sites.json`.
Install Tor: `choco install tor` (Windows) or `apt install tor` (Linux).

### Code Governance Gate
```bash
# Check a PR for injection/security issues
python scripts/security/code_governance_gate.py check-pr 752

# Check local changes before pushing
python scripts/security/code_governance_gate.py check-push

# Check diff against a ref
python scripts/security/code_governance_gate.py check-diff HEAD~3
```

Owner (issdandavis) gets WARN on findings. Non-owners get BLOCK on critical findings.
Trusted external sites: `config/security/trusted_external_sites.json`.

### Credentials (env file)
All credentials live in `config/connector_oauth/.env.connector.oauth`. Keys available:
- `PROTONMAIL_BRIDGE_PASSWORD` / `PROTONMAIL_USER` — email via Bridge IMAP
- `GMAIL_APP_PASSWORD` / `GMAIL_USER` — Gmail via IMAP SSL
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` — YouTube Data API
- `HF_TOKEN` — HuggingFace
- `GEMINI_API_KEY` — Google Gemini
- `BLUESKY_HANDLE` / `BLUESKY_APP_PASSWORD` — Bluesky posting

ProtonMail Bridge must be running locally for email access (port 1143).

### YouTube Publish & Review
```bash
# Review all your uploaded videos (scores title, description, transcript, tags)
python scripts/apollo/video_review.py review-all

# Pull transcripts from your own channel for training
# (uses cached transcripts from training-data/apollo/youtube_transcripts/)
```

Review scores: title (structure, length, searchability), description (depth, links, hashtags),
transcript (speaking rate, vocabulary richness, technical density), tags (count, brand coverage).
Reports saved to `artifacts/apollo/video_reviews/`.
