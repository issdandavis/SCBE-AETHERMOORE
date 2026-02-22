# System Access Audit — 2026-02-22

## Scope
Audit of available system access from the current automation environment for:
- GitHub
- Notion
- Google Drive

## Results

### GitHub — Accessible
- Auth status: `gh auth status` confirms active account `issdandavis` with `repo` and `workflow` scopes.
- MCP check: `docker mcp tools call get_me {}` returns the same GitHub identity.
- Repository visibility confirmed:
  - `issdandavis/SCBE-AETHERMOORE` (default branch: `main`)
  - 53 public repos listed under account.
- Active PR discovered:
  - `#247` on `feat/hydra-tests-and-3gap`.
- Workflow visibility confirmed:
  - 40+ workflows available.
  - Recent recurring failures observed in `.github/workflows/weekly-security-audit.yml` runs on feature branch pushes.

### Notion — Partially Accessible
- Direct Notion MCP API (`mcp__notion__API-*`) failed with `401 unauthorized` due to invalid API token.
- Zapier Notion connector works:
  - Successfully retrieved page `2d7f96de82e5803eb8a4ec918262b980`.
  - Page title and metadata resolved successfully.
- Codex Notion fetch connector works:
  - Returned page content and child-page references.

### Google Drive — Accessible (via Zapier)
- Google Drive connector lookup and operations succeeded.
- File discovery succeeded for `SCBE` query.
- Permission query succeeded for file `1u42f6GV5ESKwzfcoj-CyG-KzI5FzlE5a`.
- Ownership and metadata are available for automation workflows.

## Operational Conclusion
- **GitHub:** ready for full automation.
- **Drive:** ready for full automation.
- **Notion:** use Zapier/Codex routes now; direct Notion token must be repaired.

## Required Fixes (Priority)
1. Re-authenticate/rotate direct Notion API token for `mcp__notion__API-*` tools.
2. Keep Zapier Notion route as fallback path in production scripts.
3. Add connector health checks to nightly runbook:
   - GitHub identity check
   - Notion page fetch test
   - Drive file find test
