# Security Policy

## Reporting

If you discover a security issue in SCBE-AETHERMOORE:

1. Prefer GitHub security reporting or a private maintainer contact channel if available.
2. Do not publish working exploit details in a public issue before the problem is understood and mitigated.
3. Include:
   - affected path or component
   - impact
   - reproduction steps
   - whether the issue is local-only, CI-only, or runtime-exposed

## Scope

Security-sensitive areas in this repository include:
- input parsing and HTML / URL handling
- training-data ingest and export tooling
- cryptographic helpers and envelope logic
- GitHub Actions and workflow permissions
- connector and secret-handling scripts
- agent or browser automation surfaces that execute commands or process remote content

## Handling Expectations

- Secrets should stay in environment variables or approved secret stores.
- Public fixes should remove the vulnerability first, then restore ergonomics.
- Deterministic audit paths should preserve decision-relevant metadata.

## Supported Branches

Security fixes should target the current default branch, `main`, unless a maintainer states otherwise.

## Public Issues

If a public issue is required for tracking, keep it high-level until the patch is merged. Avoid pasting tokens, credentials, or full exploit payloads.
