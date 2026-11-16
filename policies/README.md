# policies/

Governance policy data.

- `base/` — baseline control sets: `access.yaml`, `audit.yaml`, `data.yaml`.
- `profiles/` — overlays for `startup`, `regulated`, and `defense` deployments.
- `contracts/` — three "Polly clay" execution contracts: `min` (read-only), `mid` (bounded writes), `max` (high-impact, requires human approval metadata).
- `releases/manifest.json` — which base and profile make up the current policy pack, with release history.
- `ai_estate_policy.json` — AI estate policy record.

The YAML files have no header comments; their structure is `{id, version, controls}`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/policies.md`](../docs/file-index/policies.md).
