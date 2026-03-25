# Swarm Telemetry and Notion Mapping

Date: 2026-03-24
Repo: SCBE-AETHERMOORE
Purpose: unify the swarm formation docs, runtime formation code, telemetry surface, and Notion export manifest into one operational map.

## 1. Why this exists

The repo already has the pieces:
- formation language in docs
- formation primitives in code
- telemetry hooks in the browser and runner lanes
- Notion export metadata describing canonical pages

What was missing was the bridge.

This spec creates that bridge so the load harness and future dashboards can speak one language.

## 2. Important architectural finding

The docs and the live code are not using the same formation vocabulary.

Docs formation names:
- Hexagonal Ring
- Tetrahedral
- Concentric Rings
- Adaptive Scatter

Live TypeScript formation names:
- `defensive_circle`
- `investigation_wedge`
- `pursuit_line`
- `consensus_ring`
- `patrol_grid`

This is not a bug by itself. It is a taxonomy split.
The right fix is normalization, not deletion.

## 3. Normalized formation families

Use these canonical formation families for telemetry:

1. `perimeter_ring`
- doc aliases: `Hexagonal Ring`
- code aliases: `defensive_circle`, parts of `consensus_ring`
- purpose: protect center, equal-distance perimeter, broadcast safety

2. `hierarchical_shell`
- doc aliases: `Concentric Rings`
- code aliases: future extension of `consensus_ring` or multi-ring deployment
- purpose: tiered trust, IP rings, inner vs outer authority layers

3. `three_dimensional_resilience`
- doc aliases: `Tetrahedral`
- code aliases: no direct current TS primitive, but valid runtime family for 3D fleet deployment
- purpose: separation, fault tolerance, altitude/depth-aware coordination

4. `focused_probe`
- doc aliases: none exact
- code aliases: `investigation_wedge`, `pursuit_line`
- purpose: inspect suspicious targets, follow moving adversaries, high-trust forward edge

5. `coverage_mesh`
- doc aliases: parts of `Adaptive Scatter`
- code aliases: `patrol_grid`
- purpose: continuous area coverage and watchkeeping

6. `adaptive_field`
- doc aliases: `Adaptive Scatter`
- code aliases: future dynamic orchestration layer
- purpose: jam resistance, self-organization, moving consensus field

## 4. Runtime code anchors

Primary code anchors already present:
- `src/ai_brain/swarm-formation.ts`
  - active formation types
  - formation health
  - formation coherence
  - trust-weighted vote
- `scripts/aetherbrowse_swarm_runner.py`
  - rails packet model
  - Layer 14 telemetry synthesis
  - decision records and trace output
- `src/aetherbrowser/phase_tunnel.py`
  - per-step telemetry capture during traversal

Telemetry backend constraint:
- `docs/metrics-telemetry.md` says runtime telemetry is `stdout` only today
- `datadog`, `prom`, and `otlp` are declared but not implemented

Implication:
- first implementation should emit structured JSONL or summary JSON locally
- exporter fan-out comes second

## 5. Notion export anchors

The local Notion export manifest already identifies the pages we should treat as canonical knowledge sources.

High-value keys for this telemetry map:
- `swarmDeploymentFormations`
  - docs output: `docs/SWARM_FORMATIONS.md`
  - role: primary formation canon
- `hydraMultiAgentCoordinationSystem`
  - docs output: `docs/HYDRA_COORDINATION.md`
  - role: orchestration context
- `multiAiDevelopmentCoordination`
  - docs output: `docs/MULTI_AI_COORDINATION.md`
  - role: cross-lane role mapping
- `droneFleetArchitectureUpgrades`
  - docs output: `docs/DRONE_FLEET_UPGRADES.md`
  - role: physical swarm deployment context

Recommended policy:
- use local Notion export docs as the stable vocabulary source
- only query live Notion API when a page is missing, stale, or newly created

## 6. Telemetry layers

### Layer A: Formation identity

Fields:
- `formation_id`
- `formation_family`
- `formation_type_runtime`
- `formation_type_doc`
- `formation_purpose`
- `formation_created_at`
- `enforcing_decision`
- `mission_id`
- `worker_id`
- `session_id`

### Layer B: Spatial geometry

Fields:
- `center_vector`
- `radius`
- `agent_count`
- `centroid`
- `mean_distance_to_center`
- `max_distance_to_center`
- `pairwise_distance_mean`
- `pairwise_distance_std`
- `pairwise_distortion`
- `boundary_pressure`
- `hyperbolic_spread`

Notes:
- `computeHealth()` and `computeCoherence()` in `swarm-formation.ts` already imply most of these
- for early implementation, Euclidean proxies are acceptable if hyperbolic values are not yet emitted explicitly

### Layer C: Trust and role topology

Fields:
- `leader_count`
- `wing_count`
- `support_count`
- `reserve_count`
- `trust_weight_sum`
- `trust_weight_mean`
- `trust_weight_std`
- `influence_concentration`
- `weighted_vote_allow`
- `weighted_vote_deny`
- `weighted_vote_total`

Interpretation:
- if influence concentrates too tightly, the formation is brittle
- if weighted vote swings sharply while geometry is stable, the threat is likely semantic rather than spatial

### Layer D: Operational pressure

Fields:
- `route_fast_count`
- `route_curved_count`
- `route_quarantine_count`
- `route_drop_count`
- `queue_depth_in`
- `queue_depth_out`
- `cpu_percent`
- `ram_mb`
- `gpu_util_percent`
- `gpu_mem_mb`
- `session_history_size`
- `degraded_mode_active`

Purpose:
- ties swarm behavior to the full load harness
- needed for overload and exhaustion testing

### Layer E: Detection and governance

Fields:
- `decision`
- `decision_reason`
- `verification_score`
- `risk`
- `d_star`
- `coherence`
- `session_suspicion`
- `signals_fired`
- `blocked_actions`
- `antivirus_turnstile`
- `pqc_audit_status`

Source anchor:
- `scripts/aetherbrowse_swarm_runner.py` already emits decision rails, verification metrics, antivirus state, PQC audit state, and Layer 14 summaries

### Layer F: Layer 14 comms signal

Current implemented fields in the runner:
- `energy`
- `centroid`
- `flux`
- `hf_ratio`
- `stability`
- `verification_score`
- `anomaly_ratio`
- `signal_class`
- `channel`

Use:
- keep this as the outward summary packet
- treat it as the compressed swarm pulse, not the whole telemetry body

## 7. Proposed canonical schema

### Formation packet

```json
{
  "formation_id": "formation-12",
  "formation_family": "focused_probe",
  "formation_type_runtime": "investigation_wedge",
  "formation_type_doc": null,
  "mission_id": "mission-abc",
  "session_id": "session-123",
  "purpose": "Investigating suspicious activity",
  "enforcing_decision": "QUARANTINE",
  "created_at": 1774160334
}
```

### Telemetry packet

```json
{
  "formation_id": "formation-12",
  "spatial": {
    "radius": 0.3,
    "agent_count": 6,
    "mean_distance_to_center": 0.24,
    "pairwise_distortion": 0.08,
    "hyperbolic_spread": 0.31,
    "boundary_pressure": 0.12
  },
  "trust": {
    "trust_weight_sum": 4.92,
    "trust_weight_mean": 0.82,
    "influence_concentration": 0.34,
    "weighted_vote_allow": 2.41,
    "weighted_vote_deny": 0.77,
    "weighted_vote_total": 3.18
  },
  "operations": {
    "queue_depth_in": 4,
    "queue_depth_out": 1,
    "cpu_percent": 37.2,
    "ram_mb": 914,
    "gpu_util_percent": 41.0,
    "gpu_mem_mb": 1822,
    "degraded_mode_active": false
  },
  "governance": {
    "decision": "QUARANTINE",
    "verification_score": 0.78,
    "risk": 0.22,
    "d_star": 0.49,
    "coherence": 0.88,
    "signals_fired": ["adversarial_lexical", "session_suspicion"]
  },
  "layer14": {
    "energy": 0.83,
    "centroid": 0.78,
    "flux": 0.17,
    "hf_ratio": 0.16,
    "stability": 0.88,
    "anomaly_ratio": 0.19,
    "signal_class": "quarantine"
  }
}
```

## 8. Mapping table: docs to runtime to telemetry

| Canonical family | Doc source | Runtime source | Core telemetry focus |
|---|---|---|---|
| `perimeter_ring` | `SWARM_FORMATIONS.md` Hexagonal Ring | `defensive_circle`, `consensus_ring` | symmetry, center protection, coherence |
| `hierarchical_shell` | `SWARM_FORMATIONS.md` Concentric Rings | extension / future composite | inner-ring trust, outer-ring spread, tier pressure |
| `three_dimensional_resilience` | `SWARM_FORMATIONS.md` Tetrahedral | future fleet primitive | z-depth spread, byzantine resilience |
| `focused_probe` | none exact in docs | `investigation_wedge`, `pursuit_line` | forward edge trust, target lock, drift |
| `coverage_mesh` | partial Adaptive Scatter | `patrol_grid` | coverage density, gap detection |
| `adaptive_field` | Adaptive Scatter | future orchestration layer | jitter, self-healing, jam resistance |

## 9. Creative but grounded telemetry views

These are worth building because they match the system rather than flattening it.

1. Formation pulse
- a compact Layer 14 signal per formation over time
- useful for dashboards and alarms

2. Trust pressure map
- centroid plus weighted vote plus influence concentration
- shows whether the swarm is balanced or being dragged by one edge

3. Boundary weather
- boundary pressure plus hyperbolic spread plus anomaly ratio
- shows whether the swarm is collapsing toward the wall

4. Role braid
- leader / wing / support / reserve as a temporal braid instead of a flat table
- useful for formation mutation and pursuit phases

5. Notion mirror card
- each canonical Notion page emits a structured telemetry card describing:
  - source page id
  - runtime modules
  - schema version
  - live field coverage

## 10. Recommended implementation order

1. Normalize formation taxonomy
- add `formation_family` as the canonical field
- preserve existing runtime names as `formation_type_runtime`

2. Extend decision records
- include formation packet when a swarm or fleet operation is active

3. Emit local JSONL telemetry first
- do not wait for Datadog or OTLP
- current metrics backend does not support them yet

4. Build a Notion-backed vocabulary index
- source from `notion_pages_manifest.json`
- map `notion_key -> docs_output_path -> runtime modules -> telemetry fields`

5. Add swarm load-harness overlays
- overlay CPU/RAM/GPU/queue metrics onto formation packets

## 11. Immediate next step

Build one schema file from this map:
- `formation_packet.schema.json`
- `formation_telemetry_packet.schema.json`

Then wire the load harness to emit them during:
- shadow replay
- mixed adversarial replay
- sustained flood

## 12. Bottom line

The cool part of the swarm system is not just the names or the geometry.
It is that the repo already has enough structure to make swarm telemetry legible.

This spec turns the swarm from a set of impressive pieces into a measurable control surface.
