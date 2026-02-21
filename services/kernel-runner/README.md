# Kernel Runner (Sandboxed npm Playground)

`services/kernel-runner` is a local service for running pasted Node/npm projects in an isolated Docker worker.

## Security Model (MVP)

1. Preflight gate computes `truth/useful/harmful` scores.
2. Decision emits SCBE-style records:
- `state_vector` (`coherence`, `energy`, `drift`)
- `decision_record` (`ALLOW` / `QUARANTINE` / `DENY`)
3. Execution only proceeds when decision is `ALLOW`.
4. Install stage:
- Docker container with resource limits
- `npm install --ignore-scripts`
5. Run stage:
- Fresh Docker container, network disabled (`--network none`)
- Restricted run commands: `npm test` or `npm run <script>`

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

Optional env:

- `KERNEL_RUNNER_PORT` (default `4242`)
- `KERNEL_RUNNER_IMAGE` (default `node:20-bookworm`)

