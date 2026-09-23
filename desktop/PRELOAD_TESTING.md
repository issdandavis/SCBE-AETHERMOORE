# Desktop preload compatibility

From `desktop`, using Node.js 24:

```powershell
npm install
npm run test:preloads
```

The test starts hidden Electron windows in a fresh temporary profile. It loads
the three actual preloads with sandboxing and context isolation enabled, checks
that Node is unavailable in the renderer, exercises a fixed tabs IPC response
and local-storage round trip, and checks native versus desktop API selection.
It does not launch the Python backend or contact model providers. This is an
API/preload check, not a packaged-installer or full end-to-end desktop test.

The sidepanel bridge is `window.aetherChrome`. Chromium already owns
`window.chrome`; exposing a new context bridge on that name can fail before the
sidepanel starts. Shared renderer helpers select the namespaced desktop bridge
or the native extension API through `src/extension/lib/browser-api.js`.

Electron 44 downloads its binary on first use. For offline preparation, run
`npx --no install-electron` while online, then run the smoke test. The CI workflow
`Desktop preload compatibility` repeats the Windows check for desktop and shared
API changes. Temporary test profiles use the `aether-preload-smoke-` prefix in
the operating system's temporary directory.
