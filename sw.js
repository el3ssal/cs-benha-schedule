/* sw.js — PWA service worker (must stay at the site root for scope).
 *
 * Cache strategy: cache-first for the app shell, NETWORK-FIRST for
 * data/schedule.json (with cache fallback) so students never see a stale
 * schedule forever. Bump CACHE_VERSION on every deploy that changes
 * shell files.
 */

const CACHE_VERSION = "v1";
const CACHE_NAME = "cs-benha-schedule-" + CACHE_VERSION;

const SHELL_FILES = [
  "./",
  "./index.html",
  "./css/style.css",
  "./css/print.css",
  "./js/app.js",
  "./js/data.js",
  "./manifest.json",
];

const DATA_FILES = ["./data/schedule.json", "./data/meta.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

function is_data_request(url) {
  return DATA_FILES.some((path) => url.endsWith(path.replace("./", "/")) || url.endsWith("data/schedule.json") || url.endsWith("data/meta.json"));
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (is_data_request(url.pathname)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        }),
    ),
  );
});
