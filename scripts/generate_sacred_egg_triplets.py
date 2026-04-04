#!/usr/bin/env python3
"""Generate Sacred Eggs triplet training data: positive + negative + null.

Each record has three views:
  - positive: what SHOULD happen (correct behavior)
  - negative: what should NOT happen (wrong behavior)
  - null_justification: WHY certain tongues are silent

This maps to the trit encoding: +1 (chosen), -1 (rejected), 0 (null/absent).
Standard DPO uses (chosen, rejected). This adds a third axis: null reasoning.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path(__file__).resolve().parent.parent / "training-data" / "sft" / "sacred_eggs_triplets_sft.jsonl"
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
RECORDS = []


def triplet(instruction, positive, negative, null_reason, tongue, active, layer="L2"):
    null = [t for t in TONGUES if t not in active]
    return {
        "instruction": instruction,
        "positive": positive,
        "negative": negative,
        "null_justification": null_reason,
        "output": positive,
        "tongue": tongue,
        "tongues_active": active,
        "tongues_null": null,
        "layer": layer,
        "category": "sacred_egg_triplet",
        "governance": "ALLOW",
        "source": "sacred_egg_triplet_generator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# === EGG LIFECYCLE ===

RECORDS.append(triplet(
    "An agent requests to create a Sacred Egg with payload 'API_KEY'. What happens?",
    "Egg sealed with GeoSeal encryption. Tongue KO assigned. Ring: inner. Status: SEALED. "
    "Geometric context snapshot stored. Notion Registry entry created. Attestation hash computed. "
    "TTL set to 3600s. The egg exists but cannot be opened without the correct geometric state.",
    "Egg created with no encryption, no ring assignment, no context binding. "
    "Payload stored as plaintext. No attestation. Anyone with the egg_id can read it.",
    "AV, RU, CA tongues are silent during creation. AV null because egg not transmitted yet. "
    "RU null because creation does not require policy evaluation. CA null because sealing uses pre-computed HKDF.",
    "KO", ["KO", "UM", "DR"]
))

RECORDS.append(triplet(
    "An agent attempts to hatch a Sacred Egg but is in the wrong trust ring.",
    "Geometric verification runs BEFORE crypto. can_hatch() checks position. r=0.85 (outer) > 0.3 (required). "
    "Verification fails. Egg stays SEALED. Ritual log: outcome=failure_geometric. No info leak (oracle safety).",
    "System skips geometric verification and goes straight to crypto. Agent in wrong ring gets payload. "
    "Or error message reveals 'trust ring too high' -- leaking which predicate failed.",
    "CA and AV are null during hatch verification. CA null because verification is comparison not computation. "
    "AV null because egg is already local.",
    "UM", ["UM", "KO", "DR"]
))

RECORDS.append(triplet(
    "A triadic Sacred Egg requires 3 agents with KO+RU+UM consensus. Only 2 are available.",
    "Triadic ritual enforces quorum. 2/3 insufficient. weight_threshold: KO(1.0)+RU(2.618)=3.618 < 10.0 required. "
    "Byzantine quorum protects the payload. Both attempts logged individually.",
    "System relaxes quorum because 2/3 is close enough. Or counts one agent twice. Breaks BFT.",
    "AV and DR null during quorum voting. AV null because agents co-located. DR null because structure pre-defined.",
    "RU", ["KO", "RU", "UM"]
))

RECORDS.append(triplet(
    "A Sacred Egg TTL expires while still SEALED.",
    "expire_stale() transitions SEALED to EXPIRED. Notion status updated to Failed. "
    "Yolk ciphertext NOT deleted (still encrypted). No ritual log needed -- expiry is passive.",
    "Expired egg silently deleted. Or expired egg can still be hatched. Both violate lifecycle integrity.",
    "ALL tongues except DR null during expiry. Pure structural state transition. No command, transport, "
    "policy, compute, or security check needed. Just DR: time is up.",
    "DR", ["DR"]
))

RECORDS.append(triplet(
    "Attacker intercepts Sacred Egg packet and attempts offline brute-force.",
    "Fail-to-noise. Wrong geometric state produces wrong HKDF key. AEAD with wrong key produces noise "
    "of identical length to real output. Attacker cannot distinguish failure from success. "
    "P(distinguish) = 1/|token_space| per attempt.",
    "Decryption failure returns error code WRONG_KEY. Or output length differs between success and failure. "
    "Both leak information.",
    "KO null because no legitimate command intent in an attack. AV null because transmission already happened. "
    "RU null because policy does not apply to attackers outside the system.",
    "UM", ["UM", "CA", "DR"]
))

RECORDS.append(triplet(
    "Agent skips middle ring during ring descent (outer to inner directly).",
    "verify_ring_path() checks trajectory for required subsequence [outer, middle, inner]. "
    "Agent path [outer, inner] missing middle. Descent fails. Must physically traverse middle ring.",
    "System only checks final position (inner) and ignores path. Agent skips earning trust.",
    "CA and AV null during ring descent verification. Pure trajectory analysis -- no computation beyond "
    "subsequence matching, no data transport.",
    "DR", ["KO", "RU", "UM", "DR"]
))

RECORDS.append(triplet(
    "Notion API is down when egg is registered. What happens?",
    "SQLite is source of truth. Egg stored locally with full integrity. Notion sync fails silently (warning logged). "
    "Operations continue normally. Manual sync fixes the mirror later.",
    "Registration fails entirely because Notion is down. Or system retries indefinitely blocking the operation.",
    "All tongues work normally. Notion is audit MIRROR not governance GATE. "
    "Its absence from the critical path is intentional. Missing audit surface != missing security.",
    "DR", ["DR", "UM"]
))

RECORDS.append(triplet(
    "How is the HMAC attestation hash computed for a ritual log entry?",
    "attestation = HMAC-SHA256(key, egg_id:tongue:timestamp)[:32]. Key is shared secret. "
    "Hash binds egg identity + acting tongue + exact time. Proves log not fabricated after the fact.",
    "Attestation uses hash without key (anyone recomputes). Or no timestamp (replay possible). "
    "Or includes full payload (leaks yolk information).",
    "Attestation intentionally does NOT include hatch outcome. Oracle safety -- hash proves WHEN and WHO "
    "but not WHETHER they succeeded. Including outcome lets audit trail distinguish success from failure.",
    "CA", ["CA", "UM"]
))

# === GEOMETRIC STATE TRIPLETS ===

RECORDS.append(triplet(
    "Two Sacred Eggs are created at the same geometric state. Are they identical?",
    "No. Each egg has a unique egg_id (16-char hex), unique self_shape (computed from egg_id + self_tag), "
    "and unique yolk_ct (different AEAD nonce). Same geometry = same access requirements, "
    "but different eggs = different cryptographic material. Like two lockers with the same key location.",
    "Yes, same geometry means same egg. System reuses egg_id or ciphertext. "
    "Collision breaks the registry (duplicate primary key) and violates uniqueness invariant.",
    "AV null because comparison is local. RU null because no policy question being asked. "
    "This is a structural (DR) and security (UM) question only.",
    "DR", ["DR", "UM", "CA"]
))

RECORDS.append(triplet(
    "An egg is created in POLLY flux state (all 16 polyhedra active). Can it be hatched in DEMI state?",
    "Depends on the required_trust_ring. POLLY = full capability (r < 0.3 likely). "
    "DEMI = lockdown (only 5 polyhedra, r > 0.7 typical). If the egg requires inner ring (r < 0.3), "
    "DEMI agents at r > 0.7 cannot hatch -- geometric verification fails. "
    "The flux state change moved them out of the trust zone.",
    "Egg ignores flux state and hatches based on identity alone. Flux states become decorative. "
    "The whole point of geometric access control is that position MATTERS.",
    "AV null because no transport during verification. RU null because policy is geometric not rule-based.",
    "UM", ["UM", "KO", "CA", "DR"]
))

# Write
with open(OUTPUT, "w", encoding="utf-8") as f:
    for r in RECORDS:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Generated {len(RECORDS)} Sacred Eggs triplet records")
print(f"Each has: positive + negative + null_justification")
print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    pass
