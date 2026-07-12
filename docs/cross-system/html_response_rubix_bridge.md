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
  "governance_checks": [
    "Provenance is captured before reuse.",
    "Generated HTML is reviewed as untrusted input.",
    "Scripts are sandboxed or removed before embedding.",
    "Copy/export affordances are explicit for cross-agent handoff."
  ],
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
