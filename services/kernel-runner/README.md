# Kernel Runner (Sandboxed npm Playground)

`services/kernel-runner` is a local service for running pasted Node/npm projects in an isolated Docker worker.

## Security Model

1. The service binds to `127.0.0.1` by default.
2. `/api/preflight` and `/api/run` fail closed unless
   `KERNEL_RUNNER_SHARED_SECRET` contains at least 32 UTF-8 bytes.
3. Every protected request uses HMAC-SHA-256 over the method, route, timestamp,
   random nonce, and exact request body. A bounded nonce cache rejects replay.
4. Preflight computes `truth/useful/harmful` scores.
5. Decision emits SCBE-style records:
- `state_vector` (`coherence`, `energy`, `drift`)
- `decision_record` (`ALLOW` / `QUARANTINE` / `DENY`)
6. Execution only proceeds when decision is `ALLOW`.
7. Install stage:
- Docker container with resource limits
- `npm install --ignore-scripts`
- Network is disabled unless both the request and server explicitly opt in.
8. Decision receipts bind the method, route, request digest, request nonce,
   timestamp, action, scores, confidence, and reason under HMAC-SHA-256.
9. Run stage:
- Fresh Docker container, network disabled (`--network none`)
- Restricted run commands: `npm test` or `npm run <script>`
- Capabilities dropped, no-new-privileges, read-only root, bounded tmpfs.

The HMAC and Docker boundary are authority controls. The SCBE scores are
policy telemetry and routing pressure; they do not authenticate the caller.

## API

- `GET /api/health`
- `POST /api/preflight`
- `POST /api/run`

Payload example:

```json
{
  "packageJson": {
    "name": "sandbox-demo",
    "version": "1.0.0",
    "private": true,
    "scripts": { "test": "node index.js" },
    "dependencies": { "lodash": "^4.17.21" }
  },
  "files": {
    "index.js": "const _ = require('lodash'); console.log(_.sum([1,2,3]));"
  },
  "runCommand": "npm test"
}
```

## Run

From repo root:

```powershell
node services/kernel-runner/server.mjs
```

Then open:

`http://localhost:4242`

The browser keeps the service secret in page memory only. It does not put the
secret in local storage or transmit it as a raw header.

Optional env:

- `KERNEL_RUNNER_PORT` (default `4242`)
- `KERNEL_RUNNER_HOST` (default `127.0.0.1`; widening this is an explicit exposure)
- `KERNEL_RUNNER_IMAGE` (default `node:20-bookworm`)
- `KERNEL_RUNNER_SHARED_SECRET` (required for protected routes; 32+ UTF-8 bytes)
- `KERNEL_RUNNER_ALLOW_NETWORK_INSTALL=1` (optional; default is no install network)
- `KERNEL_RUNNER_TRUST_PROXY=1` (only behind a proxy that overwrites forwarded headers)

The n8n bridge uses the same `KERNEL_RUNNER_SHARED_SECRET` and signs each
request. A remote runner is rejected by default. To use a remote host, set
`SCBE_ALLOW_REMOTE_KERNEL_RUNNER=1`; remote plain HTTP additionally requires
`SCBE_ALLOW_INSECURE_REMOTE_KERNEL_RUNNER=1` and should only travel through an
authenticated encrypted tunnel such as Tailscale.

