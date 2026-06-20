const BOOKFORGE_CACHE = "bookforge-studio-v1";
const BOOKFORGE_ASSETS = [
  "bookforge-writing-studio.html",
  "bookforge.webmanifest",
  "bookforge-sw.js",
  "static/bookforge-icon.svg",
  "static/packages/package-products.css",
  "static/packages/package-products.js",
  "downloads/kdp-bookforge-checklist.md",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(BOOKFORGE_CACHE).then((cache) => cache.addAll(BOOKFORGE_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== BOOKFORGE_CACHE).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
