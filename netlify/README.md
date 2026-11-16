# netlify/

Netlify Functions (TypeScript) for the governance receipt service.

| Function | Route |
|----------|-------|
| `governance-submit.ts` | `/api/governance/submit` |
| `governance-receipt.ts` | `/api/governance/receipts/:receipt` |
| `governance-selftest.ts` | `/api/governance/selftest` |
| `governance-worker-background.ts` | `/api/governance/process` (background worker) |
| `governance-rollup.ts` | rollup job; no route declared in the file |
| `health.ts` | `/api/health` |
| `system-manifest.ts` | `/api/system/manifest` |

`functions/_shared/` holds payload normalisation and hashing (`governance.ts`), the receipt store (`receipt-store.ts`), and JSON/CORS response helpers (`response.ts`).

None of these files has a header comment. This is separate from the Vercel functions in `api/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/netlify.md`](../docs/file-index/netlify.md).
