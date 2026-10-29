"use strict";

const CACHE_VERSION = "v1";
const SHELL_CACHE = `aethermoor-shell-${CACHE_VERSION}`;
const API_CACHE = `aethermoor-api-${CACHE_VERSION}`;
const CACHE_PREFIX = "aethermoor-";
const API_MAX_AGE_MS = 5 * 60 * 1000;
const API_MAX_ENTRIES = 50;
const NETWORK_TIMEOUT_MS = 5000;
const CORE_ASSETS = ["./", "./index.html", "./manifest.webmanifest", "./icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(CORE_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith(CACHE_PREFIX) && ![SHELL_CACHE, API_CACHE].includes(key))
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isApiPath(url) {
  return (
    url.pathname.startsWith("/v1/") ||
    url.pathname.startsWith("/api/") ||
    url.pathname === "/health"
  );
}

function mayCacheApiRequest(request, response) {
  const cacheControl = response.headers.get("cache-control") || "";
  return (
    response.ok &&
    !request.headers.has("authorization") &&
    request.credentials === "omit" &&
    !cacheControl.toLowerCase().includes("no-store")
  );
}

async function responseWithCacheTime(response) {
  const headers = new Headers(response.headers);
  headers.set("x-aethermoor-cache-time", String(Date.now()));
  return new Response(await response.clone().blob(), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function putBounded(cache, request, response) {
  await cache.put(request, await responseWithCacheTime(response));
  const keys = await cache.keys();
  while (keys.length > API_MAX_ENTRIES) {
    const oldest = keys.shift();
    if (oldest) await cache.delete(oldest);
  }
}

async function freshCachedApiResponse(cache, request) {
  const cached = await cache.match(request);
  if (!cached) return null;
  const cachedAt = Number(cached.headers.get("x-aethermoor-cache-time") || 0);
  if (!cachedAt || Date.now() - cachedAt > API_MAX_AGE_MS) {
    await cache.delete(request);
    return null;
  }
  return cached;
}

async function networkFirstApi(request) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), NETWORK_TIMEOUT_MS);
  const cache = await caches.open(API_CACHE);

  try {
    const response = await fetch(request, { signal: controller.signal });
    if (mayCacheApiRequest(request, response)) await putBounded(cache, request, response);
    return response;
  } catch (error) {
    const cached = await freshCachedApiResponse(cache, request);
    if (cached) return cached;
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = (await cache.match(request)) || (await cache.match("./index.html"));
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirstAsset(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) await cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isApiPath(url)) {
    event.respondWith(networkFirstApi(request));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
  } else {
    event.respondWith(cacheFirstAsset(request));
  }
});
