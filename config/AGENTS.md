# AGENTS.md

Purpose

- Provide default guidance for automated agents working in this repo.

General

- Keep changes minimal and scoped to the request.
- Match existing code style; avoid sweeping reformatting.
- Do not add new dependencies or network calls without approval.

Security and Crypto

- Do not weaken crypto settings (key sizes, algorithms, salt/nonce handling, AAD binding).
- Avoid logging secrets, PHI, or key material; keep error messages generic.

Testing

- Prefer targeted pytest runs, for example: `pytest tests/test_industry_grade.py::Test...`.
- If tests are skipped, state that explicitly.

Documentation

- Update docs when behavior or interfaces change.
