# Clay VQCC curriculum system map

Status: `PREPARED_ONLY`; no training, upload, checkpoint promotion, or competition submission is authorized by this map.

## Capability boundary

The build contains two bounded capabilities:

1. recount Toffoli-class operations from raw opcode windows;
2. compare two fixed-length windows under prespecified count-gap strata;
3. generalize the comparison to source families excluded from training;
4. bind a public experiment description to its measured limitation while each
   answer is used once as truth and once as a matched distractor.

Neither task is proposal ranking or circuit synthesis. The gate-count task is
an input-access sanity check. The findings task measures whether Clay retained
the question-to-result relationship instead of answer style or length.

## Nodes and edges

```text
private Kaggle corpus v2 (read-only, manifest pinned)
    -> streaming row validation + bounded lane/token sampling [new]
    -> fine-grained source-family reconstruction [new]
    -> sealed train / family-disjoint VQCC holdout IDs [new]
    -> fail-closed prepared-only intake receipt [implemented, local fixture tested]
    -> Clay parent checkpoint + canonical character/byte vocabulary [reused]
    -> input-access adapter campaign with matched arms [new campaign]
    -> balanced + natural-prevalence resource comparator [implemented]
    -> matched public-finding binding comparator [implemented]
    -> immutable per-seed receipts/checkpoints [new, not yet run]

public circuit library v145 (read-only)
    -> optional original operands/angles and independent replay

existing dyadic 48/48/48 controls
    -> preservation/retention checks only
```

## Node inventory

| Node | Authority | Status | Input | Output / consumer |
|---|---|---|---|---|
| Corpus v2 | `issacizrealdavis/clay-vqcc-research-corpus/2`; manifest `e4a9e7e9911fd8cdd8f858595a57b047402eb32a51571a54db580f4be87597c5` | verified publisher receipt; live private/ready listing; independent full bulk hash audit not repeated | 52 mounted files | bounded training rows and source metadata |
| Corpus source code | `C:\dev\kaggle-ops\datasets\clay-vqcc-research-corpus` | read-only connected repo | public source pins and owned dyadic rows | schema and provenance rules |
| Public circuit library | `manwithacat/vqcc-apache-public-circuits/145` | read-only, dataset-pinned | public KMB files | operands, angles, replay when required |
| Parent Clay packet | `issacizrealdavis/clay-input-access-efficacy-input-20261119` | reused; must remain a separate mount | parent checkpoint, model source, vocabulary | identical initialization for every arm |
| Sealed arithmetic successor | `successor_persistent_operand_context_v1_cloud_release` | terminal separate experiment; immutable | internally generated arithmetic rows | reference mechanics only; never consumes v2 |
| Streaming loader | `load_vqcc_corpus.py` | implemented; synthetic integration tested; full mount not yet run | mounted corpus v2 | validated bounded rows + hashes |
| Family split builder | `build_vqcc_split.py` | implemented; synthetic integration tested; full mount not yet run | row IDs plus source catalog | deterministic disjoint train/holdout manifest |
| Prepared intake runner | `run_readonly_intake.py` | implemented; fail-closed synthetic integration tested; full mount not yet run | pinned campaign spec plus read-only mounted corpus | atomic split/sample/task receipts only; never trains or mutates cloud state |
| Task/evaluator | `vqcc_task.py` | implemented, not trained | sealed gate-count rows and model labels | balanced accuracy, natural-prevalence accuracy, Toffoli regret, per-family/record receipts |
| Findings evaluator | `findings_task.py` | implemented, not trained | sealed experimental-finding rows and family sidecar | exact accuracy, task-macro accuracy, conditional-score margin |
| Training runner | absent | `UNKNOWN`; must be separately preregistered | parent + sealed manifest | per-arm checkpoints and receipts |

## Required matched arms

- `candidate`: VQCC rows bound to their true targets.
- `shuffled_binding`: one-to-one answer permutation within task and target-length strata.
- `equal_parameter`: same new trainable capacity without the proposed VQCC context path.
- `no_intervention`: frozen parent evaluated unchanged.
- `zero_update`: candidate architecture before any optimizer step.

Every trained arm starts from byte-identical trainable tensors for a given seed. Three seeds are mandatory. A candidate claim must exceed both the equal-parameter control and no-intervention baseline by at least two pooled standard deviations; otherwise report `UNDERPOWERED`.

## Invariants

- Public material remains provenance-labelled reference material; no public circuit is called original work.
- No target, post-outcome score, verifier result, or answer-derived feature enters the model input.
- A canonical record ID binds every view. Derived opcode/text/metric views are not counted as independent observations.
- Train and VQCC holdout source families are disjoint before sampling.
- Finding families are transitive components over exact source links,
  `family_target`, and direct `supersedes` edges. `related_cards` is retained as
  cross-reference metadata but is not a source-identity edge; treating every
  shared card as identity collapses the pinned ledger into a giant unpairable
  component.
- The existing dyadic holdout/ordinary/retention rows are not relabelled as VQCC evaluation.
- Row, character/token-proxy, sequence-length, and total-budget caps are sealed before training.
- The 25 GiB writable-target gate is unchanged.
- Training is private, offline, CPU-only unless a later exact authorization states otherwise.

## Stop conditions

Stop before training if any manifest/hash/count differs, any source family crosses the split, tokenizer coverage is incomplete, selected IDs are not reproducible, a control has unequal capacity, runtime is still unbounded, writable capacity is below 25 GiB, or explicit one-use execution authorization is absent.

## Evidence state

- `PROVEN`: corpus v2 identity/count metadata; old arithmetic packet incompatibility; need for a VQCC-family holdout; existing 25 GiB gate; fail-closed synthetic manifest-to-task integration.
- `IMPLEMENTED, NOT EXECUTED ON FULL MOUNT`: bounded loader, fine-grained split, fail-closed prepared-only intake runner, gate-count evaluator, finding-binding evaluator, machine-readable specification.
- `UNKNOWN`: final mounted sample/token counts, runtime, learning effect, proposal-ranking behavior, private-score relevance, and any circuit-score gain.
