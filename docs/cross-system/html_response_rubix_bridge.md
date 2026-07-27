# HTML Response Rubix Bridge

Source video request: `https://youtu.be/f39MnczcJZA?si=eC6znn9yMfGmnnFF` (`What if AI replies in HTML not Markdown?`). The video page was not directly retrievable from the local shell because YouTube requests were blocked by the environment proxy, so this packet preserves the applied design interpretation rather than a verbatim transcript.

## Cross-system handoff packet

```json
{
  "packet": "html_response_rubix_bridge",
  "version": "2026-07-12",
  "source": "https://youtu.be/f39MnczcJZA?si=eC6znn9yMfGmnnFF",
  "principle": "When AI output is meant to become software, ask for portable semantic HTML artifacts instead of markdown-only prose.",
  "rubix_faces": ["HTML", "CSS", "JS", "SCBE", "UX", "API"],
  "copy_targets": ["prompt", "handoff_packet"],
  "governance_checks": [
    "Provenance is captured before reuse.",
    "Generated HTML is reviewed as untrusted input.",
    "Scripts are sandboxed or removed before embedding.",
    "Copy/export affordances are explicit for cross-agent handoff."
  ],
  "state_vector_request": {
    "schema": "scbe_9d_state_request.v1",
    "status": "runtime_required",
    "engine": "src/symphonic_cipher/scbe_aethermoore/unified.py#SCBEAethermoore.create_state",
    "vector_layout": {
      "context": "xi[0..5]",
      "time": "xi[6]",
      "entropy": "xi[7]",
      "quantum": "xi[8]"
    },
    "bound_evidence": {
      "identity": ["source", "website_app", "registry_tile"],
      "intent": ["principle", "rubix_faces", "governance_checks"]
    },
    "runtime_inputs": [
      "trajectory EWMA",
      "monotonic Unix time t",
      "key-derived commitment hash",
      "trusted signature validity",
      "Hamiltonian H"
    ],
    "serialization": {
      "complex": "{ real, imag }",
      "python_dtype": "object"
    },
    "guardrails": [
      "Preserve mixed real and complex values with dtype object.",
      "Convert complex context values to magnitudes before entropy estimation.",
      "Normalize q before governance evaluation.",
      "Use real, monotonic runtime time for v4 and tau."
    ],
    "dimensions": [
      { "index": 0, "symbol": "v1", "name": "Identity", "status": "evidence_bound" },
      { "index": 1, "symbol": "v2", "name": "Intent phase", "status": "evidence_bound" },
      { "index": 2, "symbol": "v3", "name": "Trajectory", "status": "runtime_required" },
      { "index": 3, "symbol": "v4", "name": "Linear time", "status": "runtime_required" },
      { "index": 4, "symbol": "v5", "name": "Commitment", "status": "runtime_required" },
      { "index": 5, "symbol": "v6", "name": "Signature", "status": "runtime_required" },
      { "index": 6, "symbol": "tau", "name": "Time flow", "status": "runtime_required" },
      { "index": 7, "symbol": "eta", "name": "Entropy", "status": "runtime_required" },
      { "index": 8, "symbol": "q", "name": "Quantum state", "status": "runtime_required" }
    ],
    "governance_decision": "not_evaluated"
  },
  "website_app": "scbe-visual-system/components/apps/HtmlBridgeApp.tsx",
  "registry_tile": "scbe-visual-system/apps-registry.json#ai-workspace/htmlbridge"
}
```

## Prompt pattern

```html
<section class="scbe-artifact" data-format="html-response">
  <header><h2>Make the answer runnable</h2></header>
  <p>Return semantic HTML first, then CSS and JS blocks only when needed.</p>
  <button data-action="copy">Copy artifact</button>
</section>
```

## Operational note

Use the Code Rubix Cube metaphor before accepting an artifact:

1. **HTML**: Is the structure semantic and accessible?
2. **CSS**: Is presentation portable without global side effects?
3. **JS**: Is behavior minimal, inspectable, and sandbox-safe?
4. **SCBE**: Is provenance/governance metadata attached?
5. **UX**: Can a human understand and copy/export the artifact?
6. **API**: Can another system ingest the artifact without hidden dependencies?

## 9D governance preflight

The browser binds packet evidence but intentionally does not fabricate a numeric `xi` vector, entropy score, quantum state, or `ALLOW`/`DENY` result. It emits a `runtime_required` request whose layout matches the canonical engine: six context coordinates followed by `tau`, `eta`, and `q`.

The trusted Python runtime owns trajectory history, monotonic time, key-derived commitment, signature verification, entropy handling, quantum normalization, and the final governance decision. Until that evaluation runs, the packet remains explicitly `not_evaluated`.

## Website behavior

The GeoShell `HTML Bridge` app exposes separate copy controls for the reusable HTML prompt and the canonical JSON handoff packet. The packet rendered in the app uses the exact schema documented above. If clipboard access is unavailable, the app identifies the blocked target, keeps its source text visible, and expands the packet details for manual copying.
