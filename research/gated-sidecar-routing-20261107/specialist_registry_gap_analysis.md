# Specialist registry commercial gap analysis

Date: 2026-11-07  
Authority: design inventory only; no serving, routing, merge, or promotion.

## Existing layers

Clay already has three different records, and they should remain separate:

| Layer | Schema | Current role |
|---|---|---|
| Operational pointer | `clay.current-weight.v1` | Names one carrier and tokenizer; forbids implicit merge or promotion. |
| Copyless weight inventory | `clay.weight-vault.v1` | Hashes physical artifacts across local lanes without moving, deleting, training, or merging them. |
| Specialist candidate overlay | `clay.specialist-candidate-registry.v1` | Preserves verified experimental parents, controls, and trained arms as traffic-ineligible candidates. |

The verified discovery overlay contains 15 physical model artifacts plus control
aliases. Its build and independent verification proved that
`C:/dev/clay_home/weights/CURRENT.json` was unchanged. The confirmatory overlay
is correctly being finalized into a separate directory only after the running
replication and its independent verifier finish.

This separation is the right canonical arrangement. The broad vault answers
“what weights exist,” the candidate overlay answers “what evidence belongs to
this specialist experiment,” and `CURRENT.json` answers “what is operational.”
Combining those questions into one mutable file would weaken rollback and make
inactive research weights easier to expose accidentally.

## Fields already present

Each specialist artifact currently records:

- artifact, parent, and receipt hashes;
- exact path, byte size, arm, seed, and trainable parameter count;
- coding, counting, and parent-counting metrics;
- retention and evidence status;
- traffic status `INELIGIBLE` and promotion status `NOT_AUTHORIZED`;
- an explicit placeholder showing the gate contract is absent or unproven.

At registry level it also records fixed source configuration, comparison
statistics, controls, source receipts, canonical catalog receipts, and policy
proofs that no weight was copied, modified, merged, averaged, installed, served,
routed, or promoted.

## Commercial fields still missing

The current overlay is an honest research registry, not a product catalog. A
specialist cannot become sellable or deployable until a separately verified
product contract supplies all of the following:

| Missing field group | Why it is required |
|---|---|
| Stable capability ID and version | Lets customers and rollback receipts name behavior rather than a file path. |
| Backbone, architecture, tokenizer, and runtime compatibility hashes | Prevents loading a specialist against an incompatible carrier. |
| Input and output schemas | Defines whether the lane returns logits, typed actions, or evidence and how it can rejoin. |
| Eligibility and abstention contract | Makes routing auditable and prevents prompt text alone from granting traffic. |
| Source, split, license, and redistribution authority | Distinguishes owner-authorized use from artifacts that may legally ship. |
| Source-disjoint capability and false-route evidence | Measures useful routing and accidental activation outside development data. |
| Calibration, latency, memory, and capacity limits | Makes service quality and hardware cost testable. |
| Package/runtime support matrix | Binds Python/npm versions, device class, entry point, and clean-install checks. |
| Rollback and health-check contract | Proves the carrier, tokenizer, and unrelated specialists remain unchanged. |
| Customer-facing limits and support status | Prevents an experimental score from becoming an unsupported product promise. |

## Minimal additive product contract

Do not add these fields to `CURRENT.json`. Add an optional, immutable
`product_contract` object to a future specialist-registry schema. It must be
absent for historical candidates and fail closed unless every required field is
populated and independently verified. A minimal shape is:

```json
{
  "capability": {"id": "clay.coding", "version": "1.0.0"},
  "compatibility": {
    "backbone_sha256": "...",
    "architecture_sha256": "...",
    "tokenizer_sha256": "...",
    "runtime": {"python": "...", "device_class": "..."}
  },
  "interface": {
    "input_schema": "...",
    "output_schema": "typed_action_candidates.v1"
  },
  "routing": {
    "eligibility_contract_sha256": "...",
    "false_route_receipt_sha256": "...",
    "abstention_supported": true
  },
  "evidence": {
    "capability_receipt_sha256": "...",
    "retention_receipt_sha256": "...",
    "source_disjoint": true
  },
  "operations": {
    "latency_receipt_sha256": "...",
    "memory_receipt_sha256": "...",
    "rollback_receipt_sha256": "..."
  },
  "distribution": {
    "license_id": "...",
    "redistribution_authorized": false,
    "support_status": "experimental"
  }
}
```

The default remains `traffic_status: INELIGIBLE`. No field should change that
status automatically. Promotion and traffic authorization require a distinct,
human-reviewed receipt after the confirmatory, source-disjoint, false-route,
compatibility, clean-install, and operations gates all pass.

## Next implementation boundary

Do not migrate the registry schema while the confirmatory run is active. First
preserve and independently verify its v1 overlay exactly as preregistered. Then
prototype a v2 validator against copies or fixtures, with v1 candidates loading
as explicitly non-product records. This keeps the evidence pipeline stable
while making the path to a deployable package concrete.
