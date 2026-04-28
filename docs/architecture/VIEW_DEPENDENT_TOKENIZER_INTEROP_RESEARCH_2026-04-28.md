# View-Dependent Tokenizer Interop Research - 2026-04-28

## Purpose

Ground the yin-yang / anamorphic tokenizer idea in current cross-platform interpretation and integration formats used around defense, NASA-style flight software, space operations, and public SpaceX/Starlink-facing interfaces.

## Bottom Line

Do not make the view-dependent tokenizer the primary interchange format.

Use it as a frame-dependent semantic overlay that can be rendered for humans/agents, while the authoritative payload remains in existing machine formats:

- SysML v2 / KerML / Systems Modeling API for systems-model semantics.
- OpenAPI + JSON Schema for REST integration.
- Protocol Buffers / gRPC for compact typed service traffic.
- XTCE / CCDD / cFS command and telemetry dictionaries for spacecraft command/telemetry interpretation.
- CCSDS / DTN Bundle Protocol for delayed or disrupted message carriage.
- F Prime component/port definitions for small flight-software components.
- Open MCT telemetry objects for mission-operations visualization.

The yin-yang token surface should carry frame, channel, provenance, and route metadata. It should not replace the payload schema.

## Source-Grounded Signals

### DARPA

DARPA MATHBAC frames agent communication as a formal system, not just message strings. The program language emphasizes mathematics, systems theory, information theory, common protocols, and explainable evolution of agent collectives. This supports treating the SCBE view-dependent tokenizer as an agent-communication control surface, but only if it produces measurable protocols and generalizable principles.

Source: https://www.darpa.mil/research/programs/mathbac

DARPA CASTLE emphasizes automated, repeatable, measurable cyber-agent environments and open benchmark datasets. This supports fail-closed evaluation for any cross-platform interpretation layer: the tokenizer must be benchmarked under frame swaps, schema mismatch, prompt injection, stale route state, and degraded telemetry.

Source: https://www.darpa.mil/research/programs/cyber-agents-for-security-testing-and-learning-environments

### NASA

NASA cFS is explicitly platform-independent and isolates applications from operating-system and hardware-platform details. That is the correct deployment analogy: SCBE should expose adapters into platform-specific command/telemetry and flight-software layers rather than requiring those layers to become SCBE-native.

Source: https://software.nasa.gov/software/GSC-18719-1

NASA F Prime targets portable, reusable, analyzable, testable embedded/flight applications with component interfaces and ports. The view-dependent tokenizer maps naturally to component metadata, port intent, and command/telemetry role labeling, not to raw flight-control loops.

Source: https://fprime.jpl.nasa.gov/overview/

NASA DTN resources point to CCSDS Bundle Protocol, LTP, schedule-aware routing, cFS Bundle Protocol applications, and ION. This matters because view-dependent tokens need a store-and-forward envelope for disrupted networks; the active reading frame must be explicit in the bundle metadata.

Source: https://www.nasa.gov/technology/space-comms/delay-disruption-tolerant-networking-mission-resources/

NASA CCDD manages cFS command and telemetry data and imports/exports CSV, JSON, EDS, and XTCE. That gives the practical bridge for SCBE: generate or consume dictionaries rather than inventing another spacecraft dictionary format.

Source: https://github.com/nasa/CCDD

Open MCT is NASA's web-based mission-operations visualization framework and can display streaming/historical telemetry, imagery, timelines, procedures, and other visualizations. A yin-yang token viewer belongs here as a visualization/plugin layer over canonical telemetry, not as the telemetry source.

Source: https://nasa.github.io/openmct/

NASA JSC simulation pages emphasize high-fidelity, real-time, human-in-the-loop engineering simulations, hardware-in-the-loop testing, and model integration. This supports validating the tokenizer with simulation replay before any operational claim.

Source: https://www.nasa.gov/reference/jsc-simulation-modeling/

### SpaceX / Starlink Public Surface

The most relevant official public SpaceX/Starlink interface found is the Starlink Space Safety API, which exposes endpoints for conjunction screening and maneuver coordination. It groups resources around CDM, event, object, operator, and trajectory. That is directly relevant to cross-platform interpretation: SCBE should map frame-dependent route meaning into existing orbital-safety objects rather than treating "SpaceX integration" as a generic telemetry pipe.

Source: https://docs.space-safety.starlink.com/docs/category/api/

Important caveat: consumer Starlink local gRPC telemetry is widely discussed but is not a stable official integration target in the same way. Treat it as an optional observability adapter only, never as a canonical aerospace contract.

### Cross-Platform Standards

OMG SysML v2 is a formal systems-modeling specification with machine-readable artifacts, including JSON schema and KerML model interchange packages. Use it for requirements, structure, behavior, analysis cases, and verification cases.

Source: https://www.omg.org/spec/SysML/

OMG Systems Modeling API and Services is a formal API specification that separates platform-independent services from platform-specific bindings such as REST/HTTP, SOAP, Java, and .NET. This is the cleanest external pattern for SCBE: define one logical model, then bind it into multiple execution surfaces.

Source: https://www.omg.org/spec/SystemsModelingAPI/

OpenAPI remains the practical baseline for public REST contracts, including request/response objects, parameters, media types, encoding, examples, and external documentation. Use it for service-facing SCBE adapters.

Source: https://spec.openapis.org/oas/latest.html

Protocol Buffers are language-neutral, platform-neutral structured-data serialization with generated bindings and backward-compatible schema evolution. Use protobuf/gRPC for compact typed agent envelopes and high-volume local service traffic.

Source: https://protobuf.dev/overview/

OMG API4KP defines APIs for knowledge platforms and explicitly targets integration of knowledge resources, repositories, reasoners, rule engines, and knowledge-graph systems. This is relevant for SCBE's cross-surface interpretation layer because it validates the "uniform abstraction over varied knowledge artifacts" pattern.

Source: https://www.omg.org/spec/API4KP/

## Current Format Usage Map

| Layer | Current formats / systems | SCBE role | View-dependent tokenizer role |
| --- | --- | --- | --- |
| System model | SysML v2, KerML, Systems Modeling API | Represent requirements, structure, behavior, verification cases, cross-cutting relationships | Bind two readings of the same semantic node, for example KO control view vs DR transformation view |
| API contract | OpenAPI, JSON Schema | Public service boundaries and testable API behavior | Add frame metadata and route interpretation, not payload replacement |
| Typed binary messages | Protobuf / gRPC | Fast typed service traffic and generated bindings | Encode `active_frame`, `primary_tongue`, `secondary_tongue`, payload hash, and schema reference |
| Space command/telemetry dictionary | CCDD, XTCE, EDS, CSV, JSON | Canonical command/telemetry definitions | Generate view-specific annotations for command intent and transform role |
| Flight software | cFS, F Prime | Components, apps, ports, commands, telemetry | Attach semantic tags to commands/events/ports; keep flight code conventional |
| Mission ops visualization | Open MCT | Operator dashboards and historical/streaming visualization | Render the yin-yang dual-channel surface as a visual explainer over real telemetry |
| Disrupted networking | CCSDS Bundle Protocol, DTN, LTP, ION | Store-and-forward transport under outages/latency | Carry frame metadata in bundle extension/manifest fields |
| Orbital safety / conjunction | Starlink Space Safety API CDM/event/object/operator/trajectory | Public-facing orbital coordination semantics | Map active frame to route/intent interpretation for screening and coordination workflows |

## SCBE Integration Position

The view-dependent tokenizer should be specified as:

```json
{
  "schema": "scbe_view_dependent_token_v1",
  "token_id": "sha256:...",
  "surface_type": "yin_yang_rot180",
  "frames": {
    "A": {
      "active_tongue": "KO",
      "role": "control_flow",
      "schema_ref": "sysmlv2://..."
    },
    "B": {
      "active_tongue": "DR",
      "role": "transformation",
      "schema_ref": "protobuf://..."
    }
  },
  "payload_refs": [
    {
      "format": "protobuf",
      "schema": "scbe.interop.ViewTokenEnvelope",
      "sha256": "..."
    },
    {
      "format": "xtce",
      "schema": "CommandTelemetryAnnotation",
      "sha256": "..."
    }
  ],
  "visual_constraints": {
    "rotation_degrees": 180,
    "complementarity_min": 0.72,
    "stroke_density_delta_min": 0.25,
    "decode_margin_min": 0.18
  }
}
```

## Mapping To SCBE 21D

| 21D band | Meaning | Interop mapping |
| --- | --- | --- |
| 1-3 | Context/trust | source authority, schema hash, signature state |
| 4-6 | Dual-lattice perpendicular space | A-frame / B-frame separation and complementarity margin |
| 7-9 | PHDM cognitive position | semantic role, operator intent, human/agent view state |
| 10-12 | Sacred Tongues phase encoding | KO/DR or other conjugate tongue pair phase |
| 13-15 | M4 model manifold | model/tool/runtime adapter identity |
| 16-18 | Swarm composite state | agent quorum, evaluator agreement, route confidence |
| 19-21 | HYDRA ordering/meta | DTN priority, replay order, rollback/epoch metadata |

## DARPA / NASA / SpaceX Framing

Use this language:

> A standards-first semantic overlay for cross-platform agent and telemetry interpretation. The overlay permits two frame-dependent readings of the same physical or visual token surface while preserving a conventional machine-readable payload in SysML v2, protobuf, XTCE, OpenAPI, or CCSDS/DTN envelopes.

Avoid this language:

> A replacement aerospace data format.

That claim is too broad and would fight the ecosystem. The credible claim is adapter/interpreter/overlay.

## Required Gates Before Implementation Promotion

1. `G0 Spec`: define JSON schema and protobuf schema for `ViewTokenEnvelope`.
2. `G1 Deterministic round trip`: frame A and frame B decode to distinct roles but identical payload identity.
3. `G2 Visual robustness`: renderer passes contrast, density, rotation, and occlusion tests.
4. `G3 Interop projection`: export sample records to OpenAPI JSON, protobuf, XTCE-like annotation, and SysML-v2-style textual stub.
5. `G4 Safety`: invalid frame, ambiguous figure-ground, or missing schema reference returns `QUARANTINE`, never silent fallback.
6. `G5 Mission-style replay`: run simulated telemetry/command events through the overlay and prove no command semantics change unless frame metadata explicitly changes.

## Practical Build Order

1. Add `src/interop/view_token_envelope.py` with JSON schema validation and deterministic hash.
2. Add `src/tokenizer/view_dependent.py` for frame resolution only.
3. Add `scripts/render_yinyang_token.py` as an SVG renderer.
4. Add test fixtures:
   - KO/DR control-transform pair.
   - AV/UM context-redaction pair.
   - RU/CA binding-compute pair.
5. Add export adapters:
   - OpenAPI example.
   - protobuf `.proto` draft.
   - XTCE annotation draft.
   - SysML v2 textual stub.
6. Add docs/demo view for Open MCT-style dashboard integration.

## Decision

Proceed as an experimental SCBE interop overlay.

Do not merge into SS1 transport.

Do not claim SpaceX private telemetry integration. Use Starlink Space Safety API shape as a public orbital-safety integration reference and keep consumer Starlink gRPC as non-canonical observability only.
