/* globals importScripts, globbyToRegExp */
importScripts('js/lib/globby-to-regexp.js');

const version = 'v1::'; // Change if you want to regenerate the cache
const staticCacheName = version + 'static-resources';

// Cached on start
const staticFiles = [
    './js/init-service-worker.js'
];
// Cached on load
const staticPaths = [
    './images/**/*'
];

self.addEventListener('install', async event => {
    event.waitUntil(caches.open(staticCacheName).then(cache => {
        // To add single files use cache.add
        // e.g. cache.add('//cdnjs.cloudflare.com/ajax/libs/react/15.4.2/react.min.js');
        cache.addAll(staticFiles);
    }).catch(error => {
        console.debug('Error while adding cache', error);
    }));
});

self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => {
        return Promise.all(keys.filter(key => {
            // Find all the old files
            return !key.startsWith(version);
        }).map(key => {
            // Remove old files from cache
            return caches.delete(key);
        }));
    }).then(() => {
        console.debug('Service worker initialised');
    }).catch(error => {
        console.debug('Failed installing service worker', error);
    }));
});

self.addEventListener('fetch', async event => {
    const url = event.request.url.split('?')[0];
    const apiAsset = new RegExp(/api\/v2\/series\/([a-z0-9]+)\/asset\/([a-z]+)/).test(url);
    const staticAsset = staticPaths.filter(pattern => new RegExp(globbyToRegExp(pattern)).test(url)).length >= 1;

    // Try the cache or respond with fetch request
    console.debug('Fetching ' + url);
    event.respondWith(caches.open(staticCacheName).then(cache => {
        return caches.match(event.request).then(cachedResponse => {
            return cachedResponse || fetch(event.request).then(response => {
                // Only cache API and static assets
                if (apiAsset || staticAsset) {
                    console.debug('Caching ' + url);
                    cache.put(event.request, response.clone());
                }

                return response;
            }).catch(error => {
                console.debug('Error fetching from server', error);
            });
        });
    }));
});
