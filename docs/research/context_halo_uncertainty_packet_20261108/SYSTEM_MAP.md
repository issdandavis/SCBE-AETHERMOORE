# Context-halo uncertainty packet system map

Status: bounded local contract implemented; no neural attachment or capability claim

## Capability

Represent the structured subresearch around one focus value without collapsing
support, contradiction, and unresolved uncertainty into one confidence float.
Each tangent receives an exact integer mass base. Fractions are preserved, and
the packet exposes a two-axis projection:

- real axis: net support (`support - contradiction`);
- imaginary axis: unresolved uncertainty.

This is the literal executable form of an uncertainty halo around a focal
activation. It is external context metadata, not a neural activation, learned
gate, calibrated probability, or model-weight update.

## Reused nodes

| Node | Path | Reused role |
|---|---|---|
| Research packet standard | `docs/research/RESEARCH_PACKET_STANDARD.md` | source provenance, critique, validation, and claim-boundary rules |
| Context beehive | `src/storage/context_beehive_schema.py` | reversible source identity, raw pointer, polarity, and semantic overlays |
| GeoSeal v2 | `src/geoseal_v2.py` | downstream Gaussian uncertainty precedent; no direct coupling added |
| Prime-token catalog invariant | `docs/tokenizer/PRIME_TOKEN_CATALOG_SYSTEM_MAP.md` | missing evidence is `ABSENT`; correlated transforms are not independent observations |

## New node and edges

```text
focus value ID
  + sourced subresearch tangents
      source hash / URI / span / relation / evidence kind
      integer support / contradiction / uncertainty mass
  -> average correlated tangents inside each provenance group
  -> average independent provenance groups equally
  -> exact rational support, contradiction, real, and imaginary axes
  -> hash-bound context packet

packet -> retriever/router prompt context    proposed, not connected
packet -> GeoSeal sigma                      proposed, calibration required
packet -> neural tensors or model weights    no edge
```

The canonical join is `focus_id`. Every non-absent tangent carries a source
SHA-256 and provenance group. Several excerpts, encodings, or deterministic
views from one source are averaged inside that group before groups are combined,
so repetition cannot manufacture independent evidence. `ABSENT` carries no
synthetic claim, source, or integer mass and yields full unresolved uncertainty
when it is the only state.

## Exact schema and invariants

- Evidence kinds: `observed`, `inferred`, `hypothesis`, `opinion`, `absent`.
- Active mass is three non-negative integers with a strictly positive sum.
- Support, contradiction, and uncertainty fractions always sum to one within a
  tangent and within every aggregate.
- Exact numerators and denominators are authoritative; float values are display
  projections only.
- Packet order is deterministic and hash-bound.
- Confidence is not inferred from confident wording.
- Supervision, reward, labels, and post-outcome fields have no packet slot.
- Same-source tangents remain visible but do not increase the independent
  provenance-group count.

## Downstream problem and required controls

The packet can make structured context inspectable, but its integer masses are
human/tool assignments and are not calibrated probabilities. Any later neural
attachment must compare aligned packets against provenance-preserving shuffled
bindings, no-packet input, equal-width noise, and source-family ablations on a
source-disjoint holdout. A GeoSeal adapter must preregister how exact uncertainty
fractions map to `sigma`; using `1-confidence` without calibration is not
authorized.

## Verification and rollback

Focused tests cover exact fraction arithmetic, correlated-source de-duplication,
explicit absence, invalid mass rejection, duplicate rejection, and deterministic
packet identity. Rollback is removal from future consumers; no existing storage
schema, catalog, E92 candidate, checkpoint, probability table, serving pointer,
or neural weight is changed.

Verification on 2026-11-08:

- `python -m ruff check src/storage/uncertainty_context_packet.py tests/storage/test_uncertainty_context_packet.py` -- passed;
- `python -m pytest tests/storage/test_uncertainty_context_packet.py tests/storage/test_context_beehive_schema.py -q` -- 10 passed.
