# Held-context system map

Status: isolated executable candidate; cross-language interop measured; no
active model-weight or action-authority edge

## Data and control flow

```text
source bytes + verified source identity
        |
        v
Python linguistic adapter
  observed exact-byte lane -----------+
  derived token lane                  |
  route/geometry lane (optional)      |
        |                              |
        +--> canonical HCTX packet <--+
                    |
          +---------+---------+----------------+
          |                   |                |
          v                   v                v
   Rust bounded cache    C validator      Java codec
   snapshot / restore    hot scan         portable bridge
          |
          v
Python bounded model view
  token IDs + lane IDs + spans + route values
  exact payload remains separately addressable
          |
          v
Intermodel token bridge
  exact byte seams across tokenizers
  byte-prefix token paths
  weight-derived radial cells
  collision-safe honeycomb sub-addresses
  local centroid / residual / six-direction halo ledger
```

## Existing nodes reused

| Node | Reused rule |
|---|---|
| `src/storage/uncertainty_context_packet.py` | absence remains explicit; provenance groups are not fake independent evidence |
| `docs/CANONICAL_SYSTEM_STATE.md` | name the runtime; executed code/tests outrank narrative |
| SCBE 9D integration review | typed fields and explicit numeric adapters; phase/geometry are diagnostics, not authority |
| Layer 4 / Layer 6 concepts | geometry may route and breathing may bound an aperture; neither silently becomes storage truth |
| prime-token capacity guardrail | deterministic views can improve structure but cannot add Shannon information |
| typed token honeycomb | shared cells are occupancy; exact byte paths and local slots preserve identity |

## Four planes

| Plane | This candidate's role |
|---|---|
| Carrier/compiler | canonical packet bytes, lane types, exact token IDs, provenance |
| Learned | `model_adapter.py` supplies bounded framework-neutral inputs; no learned attachment yet |
| Geometric | Q1e6 route coordinates and radius are optional metadata for explicit adapters |
| Governance | absent here; any action still requires the existing deterministic compiler and policy boundary |

## Fourteen-layer seam

This candidate does not claim byte-identical integration with every registered
14-layer profile. A later adapter must name one of `TS_PIPELINE14`,
`PY_REFERENCE14`, or `PY_FULL14` and then test these explicit edges:

```text
HCTX route lane   -> Layer 4 geometric routing input
HCTX radius       -> Layer 5 distance input
HCTX breath Q1e6  -> Layer 6 bounded transform parameter
HCTX token lanes  -> learned/action input adapter
HCTX provenance   -> receipt/governance evidence, never a permission by itself
```

No edge is implied merely because the fields exist. The current Python model
view preserves lane spans and evidence codes so a controlled learned attachment
can distinguish rigid source bytes from derived or computed views.

## Promotion gates

1. Keep the golden-vector interop test green in all four languages.
2. Fuzz malformed lengths, enum values, varints, and snapshot restore.
3. Integrate one named 14-layer profile through an explicit adapter.
4. Compare learned use against no-packet, shuffled-binding, equal-width noise,
   and source-disjoint controls.
5. Beat both a size-matched control and the existing baseline across multiple
   seeds before claiming a model gain.
6. Keep compression claims separate from learning claims.
