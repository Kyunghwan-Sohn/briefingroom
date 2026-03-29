const CACHE_NAME = 'govbrief-v4';

// 설치: 즉시 활성화
self.addEventListener('install', e => {
  e.waitUntil(self.skipWaiting());
});

// 활성화: 이전 캐시 전부 삭제
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// 요청 처리
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // HTML 페이지 → network-first (항상 최신 우선)
  if (e.request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return resp;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  // data/*.json → stale-while-revalidate (캐시 먼저 + 백그라운드 갱신)
  if (url.pathname.startsWith('/data/') && url.pathname.endsWith('.json')) {
    e.respondWith(
      caches.open(CACHE_NAME).then(cache =>
        cache.match(e.request).then(cached => {
          const fetched = fetch(e.request).then(resp => {
            if (resp.ok) cache.put(e.request, resp.clone());
            return resp;
          }).catch(() => cached);
          return cached || fetched;
        })
      )
    );
    return;
  }

  // 기타 정적 자산 → cache-first
  if (e.request.method === 'GET' && url.origin === location.origin) {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request))
    );
  }
});
