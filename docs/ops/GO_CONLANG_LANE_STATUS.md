# Go Conlang Lane Status

Status: working cell. This is evidence for later consolidation, not a tree-trim directive.

## Verified Cell

- Toolchain: Go `1.26.4` installed at `C:\Program Files\Go\bin\go.exe`.
- Windows PATH: machine PATH contains `C:\Program Files\Go\bin`; already-open shells may need a restart to see `go`.
- Compiler smoke: `go test fmt` passed.
- SCBE runtime lane: `python/scbe/tongue_code_lanes.py` includes Go as a DR/Draumric `language_family` lane.
- AetherDesk API lane: `/api/coding/guide` exposes Go as a portable service/CLI/backend language.
- AetherDesk shell lane: `shell:go_version` runs the installed Go binary directly as a read-only toolchain proof.

## Test Evidence

- `python -m pytest tests\governance\test_go_code_lane.py tests\governance\test_ca_opcode_table.py -q` -> 7 passed.
- `npm run test:aetherdesk` -> 124 passed.
- `go test fmt` -> ok.
- AetherDesk live receipt: `artifacts/aetherdesk_receipts/20260702T034659Z_shell_go_version.json` -> `go version go1.26.4 windows/amd64`.

## Consolidation Rule

- Keep `computational_isomorphism` strict; it remains the narrow contract profile.
- Use `language_family` when a tongue can validly govern multiple implementation languages.
- Do not trim repositories by language name alone. Promote or remove cells only after they have a code surface, an API or CLI surface, and focused tests.
- The old board-game Go training/evaluator files are not Golang evidence unless a test explicitly routes them through this toolchain lane.
