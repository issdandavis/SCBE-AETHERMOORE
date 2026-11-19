# src/rollout/

Deployment safety primitives in TypeScript: `canary.ts` (`CanaryManager`, traffic levels 5 → 25 → 50 → 100 % with a soak window between steps) and `circuitBreaker.ts` (`CircuitBreaker`, opens when the failure rate exceeds a threshold, default 0.5 %). Neither file has a header comment.

File-by-file descriptions: [`docs/file-index/src.md`](../../docs/file-index/src.md).
