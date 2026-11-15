# Held Context Polyglot v1

This experiment provides one byte-exact held-context object across four
languages and a structure-aware lossless compressor named **HCTX Seam-Sieve**.
It is an isolated candidate, not yet a promoted SCBE runtime or a learned Clay
weight update.

The adjacent intermodel bridge now maps model tokens back to exact packet bytes
and places them in a collision-safe weighted nest. See
`../../docs/tokenizer/INTERMODEL_BINARY_TOKEN_LEDGER.md`. The held-context
packet remains the carrier; the nest is a derived routing/index surface.

## Working surfaces

| Surface | Responsibility | Authority boundary |
|---|---|---|
| Rust | bounded cache, deterministic eviction, pinning, generation checks, snapshots | owns cache state; does not interpret language |
| Python | packet codec, linguistic lanes, bounded model view, Seam-Sieve | owns reference semantics; does not authorize actions |
| C | dependency-free strict validator and fast scan | validates only; never owns state or policy |
| Java | portable decoder/encoder and integration check | transports exact packets; never owns cache eviction |

The packet keeps `PRESENT`, `MISSING`, `NEUTRAL`, `SILENCE`, and `ABSTAIN`
distinct. It also declares every lane as independent, derived, control,
observed, computed, or provenance-bearing. Geometry is fixed-point routing
metadata. It cannot grant permission or manufacture source information.

## Run it

From this directory:

```powershell
Push-Location python
python -m unittest -v test_held_context.py test_model_adapter.py test_sieve_codec.py
Pop-Location

Push-Location rust
cargo fmt --check
cargo test
cargo clippy --all-targets -- -D warnings
Pop-Location

python verify_interop.py
python benchmark_compression.py --repeats 3
```

`verify_interop.py` compiles Rust, C (with `zig cc`), and Java into a temporary
directory. It then requires all four implementations to reproduce the same
597-byte golden vector and reject a corrupted vector.

## Seam-Sieve idea

The byte is the canonical grain. Alternate views remain attached to the same
identity, but deterministic views are not stored as if they were independent
information. Seam-Sieve therefore performs four reversible operations before a
standard entropy coder runs:

1. repeated provenance hashes become dictionary references;
2. lane IDs, radial coordinates, and token IDs become bounded deltas/varints;
3. typed lane state becomes one packed metadata word;
4. a derived byte/u16/u32 token stream that is *proven* to be reconstructed
   from an earlier exact-byte lane becomes a reference to that lane.

The fourth operation is the main gain. It applies the information-theory rule
already used elsewhere in the architecture: a deterministic representation
does not add Shannon information. The original canonical packet is regenerated,
including all CRCs, and compared byte-for-byte after every benchmark decode.

See [FORMAT.md](FORMAT.md), [SYSTEM_MAP.md](SYSTEM_MAP.md), and
[RESULTS.md](RESULTS.md).
