// Service Worker for Background Location Tracking
// Version 1.0.0

const CACHE_NAME = 'hrms-location-tracker-v1';
const API_BASE = '/employees/api/';

// Install event
self.addEventListener('install', event => {
    console.log('Location Tracking Service Worker installing...');
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', event => {
    console.log('Location Tracking Service Worker activated');
    event.waitUntil(self.clients.claim());
});

// Background sync for location data
self.addEventListener('sync', event => {
    if (event.tag === 'background-location-sync') {
        event.waitUntil(syncLocationData());
    }
});

// Periodic background sync (requires registration from main thread)
self.addEventListener('periodicsync', event => {
    if (event.tag === 'hourly-location-track') {
        event.waitUntil(performHourlyLocationTrack());
    }
});

// Message handling from main thread
self.addEventListener('message', event => {
    const { type, data } = event.data;
    
    switch (type) {
        case 'START_BACKGROUND_TRACKING':
            startBackgroundTracking(data);
            break;
        case 'STOP_BACKGROUND_TRACKING':
            stopBackgroundTracking();
            break;
        case 'SYNC_LOCATION_NOW':
            syncLocationData();
            break;
    }
});

// Background location tracking state
let trackingState = {
    isActive: false,
    employeeId: null,
    clockInTime: null,
    lastLocationTime: null,
    intervalId: null
};

// Start background tracking
async function startBackgroundTracking(config) {
    console.log('Starting background location tracking...', config);
    
    trackingState.isActive = true;
    trackingState.employeeId = config.employeeId;
    trackingState.clockInTime = config.clockInTime;
    trackingState.lastLocationTime = config.lastLocationTime;
    
    // Store config in IndexedDB for persistence
    await storeTrackingConfig(config);
    
    // Start periodic location capture
    scheduleNextLocationCapture();
    
    // Register periodic background sync if supported
    if ('serviceWorker' in navigator && 'periodicSync' in window.ServiceWorkerRegistration.prototype) {
        try {
            const registration = await navigator.serviceWorker.ready;
            await registration.periodicSync.register('hourly-location-track', {
                minInterval: 60 * 60 * 1000, // 1 hour
            });
            console.log('Periodic background sync registered');
        } catch (error) {
            console.log('Periodic background sync not supported:', error);
        }
    }
}

// Stop background tracking
async function stopBackgroundTracking() {
    console.log('Stopping background location tracking...');
    
    trackingState.isActive = false;
    
    if (trackingState.intervalId) {
        clearTimeout(trackingState.intervalId);
        trackingState.intervalId = null;
    }
    
    // Clear stored config
    await clearTrackingConfig();
    
    // Unregister periodic sync
    try {
        const registration = await navigator.serviceWorker.ready;
        await registration.periodicSync.unregister('hourly-location-track');
    } catch (error) {
        console.log('Error unregistering periodic sync:', error);
    }
}

// Schedule next location capture
function scheduleNextLocationCapture() {
    if (!trackingState.isActive) return;
    
    const now = new Date();
    const nextHour = new Date(now);
    nextHour.setHours(now.getHours() + 1, 0, 0, 0);
    
    const timeUntilNextHour = nextHour.getTime() - now.getTime();
    
    console.log(`Next location capture scheduled in ${Math.round(timeUntilNextHour / 1000 / 60)} minutes`);
    
    trackingState.intervalId = setTimeout(() => {
        performHourlyLocationTrack();
        scheduleNextLocationCapture(); // Schedule next one
    }, timeUntilNextHour);
}

// Perform hourly location tracking
async function performHourlyLocationTrack() {
    if (!trackingState.isActive) return;
    
    console.log('Performing hourly location track...');
    
    try {
        // Check if still clocked in
        const statusResponse = await fetch(`${API_BASE}location-tracking-status/`, {
            method: 'GET',
            credentials: 'include'
        });
        
        if (!statusResponse.ok) {
            throw new Error('Failed to check tracking status');
        }
        
        const statusData = await statusResponse.json();
        
        if (!statusData.is_clocked_in || statusData.tracking_stopped) {
            console.log('Employee no longer clocked in, stopping background tracking');
            await stopBackgroundTracking();
            return;
        }
        
        if (!statusData.needs_location) {
            console.log('Location update not needed yet');
            return;
        }
        
        // Get current location
        const position = await getCurrentPosition();
        
        if (position) {
            await submitLocationData(position);
            trackingState.lastLocationTime = new Date().toISOString();
            
            // Show notification to user
            showLocationUpdateNotification();
        }
        
    } catch (error) {
        console.error('Error in hourly location track:', error);
        
        // Store failed attempt for later sync
        await storeFailedLocationAttempt({
            timestamp: new Date().toISOString(),
            error: error.message
        });
    }
}

// Get current position with high accuracy
function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation not supported'));
            return;
        }
        
        const options = {
            enableHighAccuracy: true,
            timeout: 30000, // 30 seconds
            maximumAge: 0 // No cached positions
        };
        
        navigator.geolocation.getCurrentPosition(
            position => resolve(position),
            error => reject(error),
            options
        );
    });
}

// Submit location data to server
async function submitLocationData(position) {
    const locationData = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        timestamp: new Date().toISOString()
    };
    
    try {
        const response = await fetch(`${API_BASE}submit-hourly-location/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(locationData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Location submitted successfully:', result);
        
        return result;
        
    } catch (error) {
        console.error('Failed to submit location:', error);
        
        // Store for background sync
        await storeLocationForSync(locationData);
        
        // Register background sync
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            const registration = await navigator.serviceWorker.ready;
            await registration.sync.register('background-location-sync');
        }
        
        throw error;
    }
}

// Sync stored location data
async function syncLocationData() {
    console.log('Syncing stored location data...');
    
    try {
        const storedLocations = await getStoredLocations();
        
        for (const locationData of storedLocations) {
            try {
                await submitLocationData(locationData);
                await removeStoredLocation(locationData.id);
            } catch (error) {
                console.error('Failed to sync location:', error);
            }
        }
        
    } catch (error) {
        console.error('Error syncing location data:', error);
    }
}

// Show notification to user
function showLocationUpdateNotification() {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Location Updated', {
            body: 'Your location has been automatically tracked for attendance.',
            icon: '/static/img/petabytz_logo.jpg',
            badge: '/static/img/petabytz_logo.jpg',
            tag: 'location-update',
            silent: true
        });
    }
}

// IndexedDB operations for persistence
async function storeTrackingConfig(config) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['config'], 'readwrite');
            const store = transaction.objectStore('config');
            
            store.put({ id: 'tracking-config', ...config });
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
        
        request.onupgradeneeded = () => {
            const db = request.result;
            
            if (!db.objectStoreNames.contains('config')) {
                db.createObjectStore('config', { keyPath: 'id' });
            }
            
            if (!db.objectStoreNames.contains('locations')) {
                const locationStore = db.createObjectStore('locations', { keyPath: 'id', autoIncrement: true });
                locationStore.createIndex('timestamp', 'timestamp');
            }
            
            if (!db.objectStoreNames.contains('failed-attempts')) {
                db.createObjectStore('failed-attempts', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

async function clearTrackingConfig() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['config'], 'readwrite');
            const store = transaction.objectStore('config');
            
            store.delete('tracking-config');
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}

async function storeLocationForSync(locationData) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['locations'], 'readwrite');
            const store = transaction.objectStore('locations');
            
            store.add(locationData);
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}

async function getStoredLocations() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['locations'], 'readonly');
            const store = transaction.objectStore('locations');
            
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => resolve(getAllRequest.result);
            getAllRequest.onerror = () => reject(getAllRequest.error);
        };
    });
}

async function removeStoredLocation(id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['locations'], 'readwrite');
            const store = transaction.objectStore('locations');
            
            store.delete(id);
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}

async function storeFailedLocationAttempt(attemptData) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('HRMSLocationTracker', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['failed-attempts'], 'readwrite');
            const store = transaction.objectStore('failed-attempts');
            
            store.add(attemptData);
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
    });
}