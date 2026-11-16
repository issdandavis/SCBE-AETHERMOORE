# config/

Configuration data read by scripts, training jobs, and evaluators. No executable code.

| Folder | Contents |
|--------|----------|
| `model_training/` | QLoRA / SFT training profiles and evaluation contracts (39 files) |
| `eval/` | Scoring definitions: coding score, programmer index, external task lanes |
| `system/` | Dispatch capability maps and work-packet templates for the multi-agent tooling |
| `security/` | Trusted and blocked host lists and security event policy |
| `governance/` | Terminal AI router profiles (provider order and complexity tiers) |
| `training/`, `research/`, `compliance/` | Source catalogs and registries |
| `code_prism/` | Language interoperability matrix |
| `ollama/` | Modelfile and knowledge base for the local AetherBot model |
| `tor/` | Hardened `torrc` and the hidden-service hostname |
| `.kiro/`, `.claude/`, `.github/` | Copies of editor and agent tool configuration |

About half the JSON files carry no `description` field; the file index lists their top-level keys. `configs/` (plural, at the repo root) is a separate one-file directory.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/config.md`](../docs/file-index/config.md).
