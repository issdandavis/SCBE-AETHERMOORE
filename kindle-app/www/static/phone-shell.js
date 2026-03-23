window.PhoneShell = (() => {
  const isKindleApp = typeof window.Capacitor !== "undefined";
  const localhostNames = new Set(["", "localhost", "127.0.0.1", "10.0.2.2"]);
  const runtimeHost = isKindleApp
    ? "10.0.2.2"
    : (localhostNames.has(window.location.hostname) ? "127.0.0.1" : window.location.hostname);

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function readJson(response) {
    return response.text().then((text) => {
      const contentType = response.headers.get("content-type") || "";
      if (text && contentType.includes("application/json")) {
        return JSON.parse(text);
      }
      if (!text) {
        return {};
      }
      throw new Error(`${response.url} returned ${response.status} and did not send JSON.`);
    });
  }

  function readStorageJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeStorageJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function normaliseUrl(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) return "";
    if (trimmed.startsWith("./") || trimmed.startsWith("../") || trimmed.startsWith("/")) {
      return new URL(trimmed, window.location.href).toString();
    }
    if (/^[a-z]+:\/\//i.test(trimmed)) {
      return trimmed;
    }
    if (/^[a-z]+:/i.test(trimmed)) {
      return trimmed;
    }
    return `https://${trimmed}`;
  }

  function runtimeLabel() {
    return isKindleApp ? "native app / emulator" : "browser preview";
  }

  function bridgeBase(port = 8001) {
    return `http://${runtimeHost}:${port}`;
  }

  function setSharedTarget(payload) {
    const record = {
      url: payload.url || "",
      title: payload.title || "",
      note: payload.note || "",
      source: payload.source || "unknown",
      savedAt: new Date().toISOString(),
    };
    writeStorageJson("scbe.phone.sharedTarget.v1", record);
    return record;
  }

  function getSharedTarget() {
    return readStorageJson("scbe.phone.sharedTarget.v1", null);
  }

  return {
    isKindleApp,
    runtimeHost,
    runtimeLabel,
    escapeHtml,
    readJson,
    readStorageJson,
    writeStorageJson,
    normaliseUrl,
    bridgeBase,
    setSharedTarget,
    getSharedTarget,
  };
})();
