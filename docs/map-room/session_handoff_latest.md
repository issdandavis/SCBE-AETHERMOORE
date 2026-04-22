# Session Handoff — 2026-04-21

## Objective
Refresh website content to reflect recent milestones and add a free, offline-capable sidebar chatbot with curated docs, navigation, and web-search tools.

## Completed
- Back-of-house private log provisioned: `issdandavis/scbe-backofhouse` + appender `scripts/agents/log.sh` + pointer `ops/agents/README.md`.
- Ground-truth check on website members-lane claim: falsified (4 SHAs fictional, PR #1123 is email-triage not members).
- Three MATHBAC artifacts written to `docs/proposals/DARPA_MATHBAC/` (timeline, Collin asks, demo readiness).
- Phase plan + decision log + this handoff.
- Iter 1 (SHA `af236ccb`): milestones section + offline corpus chatbot landed on origin.
- Iter 2 (SHA `9911f6e4`): slash commands (/nav, /search, /help, /sections) + DuckDuckGo instant-answer + freeform intent parser; polly-sidebar.css restored.
- Iter 3 (SHA `3882f146`): HF Space source at `space/scbe-chat/` (app.py, requirements.txt, README.md, Dockerfile). Deploy is owner-only (no autonomous HF push).
- Iter 4 (SHA `6297cd6d`): a11y (aria-label send/input, aria-expanded launcher, Ctrl+/ global, Esc-to-close, focus-on-open), `docs/CHATBOT_SETUP.md`, corpus bumped to v2 with 59 passages.
- Iter 5 (SHA `5485f6d8`): favicon.svg (fixes existing 404), sitemap.xml (index + chat), robots.txt (allow all, link sitemap), favicon wired into chat.html.
- Iter 6 (SHA `7b10d36d`): brand hero.svg (1200x630, phi rings, tagline); swapped og:image, twitter:image, and offer-hero `<img>` from the missing hero.png to hero.svg.
- Iter 7 (SHA `7d276ffe`): nav bar + hero CTA link hygiene (15 broken internal links fixed). Enterprise/Contact→mailto, Pricing→#choose-path, Demos/Research/Community→public GitHub surfaces, Blog→Medium, Members removed (owner-pending), Toolkit→Stripe.
- Iter 8 (SHA `4289cdf9`): full link hygiene sweep — 25+ additional broken internal links in footer, buyer slabs, deep section CTAs, and in-body anchor refs resolved to existing anchors, Stripe links, GitHub repo, or mailto. Zero broken internal links remaining on docs/index.html.
- Iter 9 (SHA `604a3cc3`): milestones copy refresh — MATHBAC card updated (Proposers Day attended 2026-04-21, teaming 2026-04-29, abstract 2026-04-30); stale "AetherBrowser in flight" card swapped for live "Polly sidebar chat · offline mode live" milestone.

## In progress
- Website polish loop open. Any further polish lands as iter N+1, one commit each, push/verify/log.

## Blocked
- Owner call still pending on `docs/members/` PIN-gate (discard vs redesign).
- HF Space deployment deferred to owner (no autonomous HF deploy from this session).

## Next actions (resume here)
1. Owner decision on HF Space deploy (create `issdandavis/scbe-polly-chat`, paste `space/scbe-chat/`, set `HF_TOKEN` secret).
2. Owner decision on `docs/members/` PIN-gate (discard vs redesign) - still never committed.
3. Outside this loop: MATHBAC punch-list continues (DRAFT_POST_CALL, DRAFT_COLLIN_ASKS, BAAT registration, v2 teaming signature 2026-04-29, abstract 2026-04-30, full proposal 2026-06-16).

## Files changed (this run)
- ADDED: `docs/map-room/phase_plan.md`
- ADDED: `docs/map-room/session_handoff_latest.md`
- ADDED: `docs/map-room/decision_log.jsonl`

## Files pending (later iterations)
- `docs/chatbot-corpus.json` (new)
- `docs/index.html` (modify, adds milestones + possibly a meta tag for corpus URL)
- `docs/static/polly-companion.js` (modify, add offline mode)
- `docs/CHATBOT_SETUP.md` (new, iter 4)
- `space/scbe-chat/app.py` (new, iter 3)
- `space/scbe-chat/requirements.txt` (new, iter 3)
- `space/scbe-chat/README.md` (new, iter 3)

## Command history for deterministic resume

```bash
# Verify branch
git status && git branch --show-current

# After each iteration
git add <paths>
git commit -m "feat(web): iter N - <desc>"
git push origin feature/cli-code-tongues
git log origin/feature/cli-code-tongues -1 --oneline
BOH_AGENT=claude-opus-4-7 scripts/agents/log.sh "iter N: <summary>" <<'EOF'
- what changed
- status: done
- next: iter N+1
EOF
```

## Assumptions
- `feature/cli-code-tongues` is the correct target branch (confirmed by `gitStatus` at session start).
- Owner is OK with chatbot showing offline mode by default on Pages until HF Space deploys.
- DDG Instant Answer API is CORS-friendly and allows browser calls (confirmed by public docs as of 2026).

## Invalidation triggers
- If Pages workflow starts excluding `docs/map-room/` or `docs/chatbot-corpus.json`, corpus loading fails → revisit.
- If DDG CORS changes, need to add a proxy endpoint to the Space.
- If owner decides to discard the chatbot entirely, roll back the iter 1 patch by reverting the branch to pre-iter-1 SHA.

## Rollback path
- Every iteration is one commit on `feature/cli-code-tongues`. To roll back: `git revert <sha>` of the commit(s) you want undone.
- No database migrations, no schema changes, no destructive file moves.
