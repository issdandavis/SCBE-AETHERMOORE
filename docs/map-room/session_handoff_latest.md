# Session Handoff — 2026-04-21

## Objective
Refresh website content to reflect recent milestones and add a free, offline-capable sidebar chatbot with curated docs, navigation, and web-search tools.

## Completed
- Back-of-house private log provisioned: `issdandavis/scbe-backofhouse` + appender `scripts/agents/log.sh` + pointer `ops/agents/README.md`.
- Ground-truth check on website members-lane claim: falsified (4 SHAs fictional, PR #1123 is email-triage not members).
- Three MATHBAC artifacts written to `docs/proposals/DARPA_MATHBAC/` (timeline, Collin asks, demo readiness).
- Phase plan + decision log + this handoff.

## In progress
- Iter 1: milestones section + offline corpus chatbot.

## Blocked
- Owner call still pending on `docs/members/` PIN-gate (discard vs redesign).
- HF Space deployment deferred to owner (no autonomous HF deploy from this session).

## Next actions (resume here)
1. Read `docs/index.html` around the existing CTA strip to find a clean insertion point for the milestones block.
2. Write `docs/chatbot-corpus.json`.
3. Patch `docs/static/polly-companion.js` with offline fallback.
4. Add milestones HTML block to `docs/index.html`.
5. Commit + push + `scripts/agents/log.sh "iter 1: ..."`.

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
