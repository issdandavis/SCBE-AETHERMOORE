# rust/

Rust crates. Each is a separate Cargo project; there is no workspace.

| Crate | What it is |
|-------|------------|
| `scbe_core/` | Poincaré-ball distance in Rust (`poincare_distance`), the experimental port of Layer 5. Has its own README; test with `npm run test:rust` |
| `ast_cube/` | AST "cube" encoder: maps syntax-tree nodes to cube faces. No header comment |
| `ast_cube_ruff/` | The same encoder on ruff's Python parser (the fast path) |
| `ast_cube_poly/` | Polyglot version on tree-sitter, with syntax validation |
| `ast_cube_poly_legacy/` | Validator pinned to tree-sitter 0.20 for grammars on the old ABI (C#, Lua, Kotlin, Swift, Zig) |
| `parse_bench/` | Parser benchmark harness |

`scripts/benchmarks/encoder_bench.py` compares the Rust encoder with the Python reference.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/rust.md`](../docs/file-index/rust.md).
