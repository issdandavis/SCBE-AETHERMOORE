# packages/

Independently publishable packages. Per the repo's code-locality rule, a command's logic lives inside its package here, not in root-level scripts.

| Package | Language | What it is |
|---------|----------|------------|
| `kernel/` | TypeScript | Pure math kernel: hyperbolic geometry, harmonic scaling, Sacred Tongues, 14-layer pipeline. **No README of its own** |
| `cli/` | Node | The SCBE CLI (governed commands, GeoSeal, tokenizer tools) |
| `agent-bus/` | Node | Typed library for governed multi-agent event routing |
| `agent-bus-py/` | Python | Python surface over the same governed event runner |
| `polly-pad-cli/` | Node | "Polly", a governed terminal workpad for AI operators |
| `polly-pad-py/` | Python | Polly Pad workspace interface |
| `sixtongues/` | Python | Standalone Sacred Tongues package |
| `bookforge/` | Python | Markdown to print-ready paperback, hardcover, and EPUB |
| `workflow-engine/` | TypeScript | Aether Desktop operation contract and workflow spec tools. **No README of its own** |

Each package with a README documents its own install and usage.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/packages.md`](../docs/file-index/packages.md).
