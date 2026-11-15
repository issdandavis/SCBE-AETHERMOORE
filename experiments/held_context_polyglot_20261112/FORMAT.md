# HeldContextPacket v1 binary contract

All integers are little-endian. CRC-32 uses the IEEE polynomial. CRCs detect
accidental corruption; they are not authentication. The 32-byte provenance
fields are externally supplied SHA-256 identities and must be verified against
the referenced source by a higher layer.

## Packet header (64 bytes)

| Offset | Width | Field |
|---:|---:|---|
| 0 | 4 | ASCII `HCTX` |
| 4 | 1 | version = 1 |
| 5 | 1 | packet flags |
| 6 | 2 | header length = 64 |
| 8 | 4 | body length |
| 12 | 2 | lane count |
| 14 | 2 | reserved = 0 |
| 16 | 8 | monotonic sequence cutoff |
| 24 | 4 | model token budget |
| 28 | 4 | signed breathing/aperture metadata, Q1e6 |
| 32 | 4 | Poincare radius metadata, Q1e6 in `[0, 1_000_000)` |
| 36 | 16 | packet ID |
| 52 | 4 | generation |
| 56 | 4 | body CRC-32 |
| 60 | 4 | CRC-32 of header bytes 0..59 |

## Lane header (96 bytes)

| Offset | Width | Field |
|---:|---:|---|
| 0 | 2 | strictly ascending lane ID |
| 2 | 1 | kind: root, linguistic, route, tool, speech, geometry, receipt, custom |
| 3 | 1 | evidence: present, missing, neutral, silence, abstain |
| 4 | 1 | role: independent, derived, control, observed, computed, provenance |
| 5 | 1 | flags: pinned, compressible, exact bytes |
| 6 | 2 | route-coordinate count |
| 8 | 4 | token-ID count |
| 12 | 4 | payload-byte count |
| 16 | 8 | expiry sequence; all ones means no expiry |
| 24 | 32 | canonical value ID |
| 56 | 32 | source hash |
| 88 | 4 | CRC-32 over bytes 0..87 plus variable data |
| 92 | 4 | reserved = 0 |

Variable data follows in this order:

1. signed i32 Q1e6 route coordinates;
2. unsigned u32 token IDs;
3. exact payload bytes.

Decoders reject trailing bytes, unknown enum values or flags, invalid ordering,
expired-at-cutoff lanes, out-of-bound declared dimensions, and every CRC
mismatch. A valid decoder must be able to encode the decoded value back to the
identical canonical packet bytes.

## Cache snapshot

Rust snapshots start with `HCCH`, bind the cache capacity and monotonic access
clock, and store entries in packet-ID order. Restore revalidates every embedded
packet and requires snapshot metadata (ID, generation, pinned state) to match
the packet. Restore is caller-capped at 64 MiB. Cache insertion is transactional:
if pinned entries prevent eviction, the old cache remains unchanged.
