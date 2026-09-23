/** Select the isolated desktop bridge or the native extension API. */
export function getBrowserApi() {
  const api = globalThis.aetherChrome ?? globalThis.chrome;
  if (!api) {
    throw new Error('AetherBrowser API is unavailable');
  }
  return api;
}
