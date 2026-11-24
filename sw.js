/* Retire old Sarkari Alert service worker; no offline caching. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil((async()=>{try{for(const key of await caches.keys()){if(key.toLowerCase().startsWith('sarkarialert'))await caches.delete(key);}}finally{await self.registration.unregister();await self.clients.claim();}})()));
