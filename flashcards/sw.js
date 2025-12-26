const CACHE_NAME = 'flashcards-v2';
const ASSETS = [
  '/flashcards/',
  '/flashcards/index.html',
  '/flashcards/stats.html',
  '/flashcards/app.js',
  '/flashcards/manifest.json'
];

// Files that should always be fetched from network (not cached)
const NETWORK_FIRST = [
  'data.js'
];

// Install - cache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip external requests (like Tailwind CDN)
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Check if this file should always be fetched from network
  const isNetworkFirst = NETWORK_FIRST.some(file => event.request.url.includes(file));

  if (isNetworkFirst) {
    // Network first, no caching for data files
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      // Return cached version or fetch from network
      return cached || fetch(event.request).then((response) => {
        // Cache new responses
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      });
    }).catch(() => {
      // Offline fallback
      if (event.request.destination === 'document') {
        return caches.match('/flashcards/index.html');
      }
    })
  );
});
