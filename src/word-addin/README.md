# SCBE Word Add-in

Reference add-in surface for testing governed document editing before broader browser-agent and multi-agent integration.

## Current baseline

- HTTPS bridge server in [server.js](/C:/Users/issda/SCBE-AETHERMOORE/src/word-addin/server.js)
- Office manifest in [manifest.xml](/C:/Users/issda/SCBE-AETHERMOORE/src/word-addin/manifest.xml)
- Taskpane UI in [taskpane](/C:/Users/issda/SCBE-AETHERMOORE/src/word-addin/taskpane)
- CI-friendly smoke tests in [tests/server.test.js](/C:/Users/issda/SCBE-AETHERMOORE/src/word-addin/tests/server.test.js)

## Commands

```powershell
npm test
npm run certs
npm start
npm run sideload
```

## What the tests prove

- bridge health endpoint responds
- root routing and manifest serving work
- manuscript loading works against repo content
- command extraction works for AI-issued edit commands

## Next integration steps

1. Add WebSocket message-contract tests for chat, sync, and clear flows.
2. Add provider-fallback tests with mocked Anthropic/OpenAI-compatible responses.
3. Run manual Word sideload smoke against the local bridge.
4. Use this add-in as the reference surface for browser-agent and multi-agent editing workflows.
