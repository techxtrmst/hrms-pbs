self.addEventListener('install', (event) => {
    self.skipWaiting();
    console.log('Location Tracking Service Worker installed');
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
    console.log('Location Tracking Service Worker activated');
});

// Periodic Background Sync (if supported) can be used to wake up the worker
// But it's limited and requires browser support.
// For now, this SW just makes the web app more "installable" as a PWA,
// which improves background persistence on mobile devices.
self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'hourly-location-punch') {
        console.log('Periodic sync triggered for location punch');
        // Note: SW cannot directly get Geolocation. 
        // It must postMessage to clients to ask them to get location.
        event.waitUntil(checkAndNotifyClients());
    }
});

async function checkAndNotifyClients() {
    const allClients = await clients.matchAll({ type: 'window' });
    for (const client of allClients) {
        client.postMessage({ type: 'REQUEST_LOCATION_PUNCH' });
    }
}
