# Solution Logic

Use the alert class to choose the repair shape. Do not treat all high-severity alerts as the same kind of problem.

## Incomplete URL Substring Sanitization

Typical smell:
- raw `in`, `startswith`, or partial-string checks against a URL
- host allowlists enforced on unparsed strings

Fix shape:
- parse with `urllib.parse.urlparse` in Python or `new URL()` in JavaScript
- require an allowed scheme
- normalize the hostname
- match exact host or dot-boundary suffix, not loose substring
- reject empty hostname, embedded credentials, or malformed URLs

Repo examples from the current alert set:
- `src/aetherbrowser/page_analyzer.py`
- `src/browser/toolkit.py`
- test fixtures under `tests/test_browser_toolkit.py`

## Bad HTML Filtering Regexp

Typical smell:
- regex trying to remove tags or sanitize user-controlled HTML

Fix shape:
- do not sanitize HTML with regex
- if you only need plain text, escape or strip to text using a parser
- if you need safe HTML, use an allowlist-based sanitizer or build DOM nodes explicitly

Repo example:
- `src/browser/toolkit.py`

## Uncontrolled Data Used In Path Expression

Typical smell:
- user-controlled path segments joined to a writable root without normalization

Fix shape:
- resolve against a fixed root
- canonicalize with `.resolve()`
- require `candidate.relative_to(root)`
- reject traversal attempts before file operations

Repo example:
- `scripts/system/ai_bridge.py`

## Clear-Text Logging Or Storage Of Sensitive Information

Typical smell:
- secrets, tokens, or credentials copied into logs, summaries, or config files

Fix shape:
- remove raw value logging
- store only a redacted preview or deterministic fingerprint
- prefer environment-variable references over persisted secret material
- make tests assert that the sensitive literal never appears

Repo examples:
- `scripts/system/sell_from_terminal.py`
- `scripts/scbe-system-cli.py`

## DOM Text Reinterpreted As HTML

Typical smell:
- `innerHTML = userControlledText`

Fix shape:
- use `textContent`
- or create text nodes explicitly
- only use `innerHTML` for trusted templates

Repo example:
- `kindle-app/www/browse.html`

## Missing Rate Limiting

Typical smell:
- public endpoint with no request or concurrency cap

Fix shape:
- add token bucket or fixed-window rate limiting
- bound per-client concurrency
- fail closed with clear `429` behavior

Repo example:
- `services/kernel-runner/server.mjs`

## Resource Exhaustion

Typical smell:
- unbounded request body, loop, queue growth, or expensive processing

Fix shape:
- cap body size
- cap queue depth
- cap execution time
- reject or shed load before the hot path saturates

Repo example:
- `services/kernel-runner/server.mjs`

## Biased Random Numbers From Cryptographically Secure Source

Typical smell:
- `secure_random % N`

Fix shape:
- use rejection sampling
- discard values in the incomplete tail of the range
- document the accepted range

Repo example:
- `src/video/watermark.ts`
