/**
 * Background Location Tracking Manager
 * Handles automatic hourly location tracking even when the browser is closed
 */

class BackgroundLocationTracker {
    constructor() {
        this.serviceWorker = null;
        this.isSupported = this.checkSupport();
        this.isActive = false;
        this.config = {
            trackingInterval: 60 * 60 * 1000, // 1 hour in milliseconds
            highAccuracy: true,
            timeout: 30000,
            maximumAge: 0
        };
    }

    // Check if background tracking is supported
    checkSupport() {
        return (
            'serviceWorker' in navigator &&
            'Notification' in window &&
            'geolocation' in navigator
        );
    }

    // Initialize the background tracker
    async initialize() {
        if (!this.isSupported) {
            console.warn('Background location tracking not supported in this browser');
            return false;
        }

        try {
            // Register service worker
            const registration = await navigator.serviceWorker.register('/static/js/sw.js', {
                scope: '/'
            });

            console.log('Service Worker registered successfully');

            // Wait for service worker to be ready
            await navigator.serviceWorker.ready;
            this.serviceWorker = registration;

            // Request notification permission
            await this.requestNotificationPermission();

            // Listen for messages from service worker
            navigator.serviceWorker.addEventListener('message', this.handleServiceWorkerMessage.bind(this));

            return true;

        } catch (error) {
            console.error('Failed to initialize background location tracker:', error);
            return false;
        }
    }

    // Request notification permission
    async requestNotificationPermission() {
        if ('Notification' in window) {
            if (Notification.permission === 'default') {
                const permission = await Notification.requestPermission();
                console.log('Notification permission:', permission);
            }
        }
    }

    // Start background location tracking
    async startTracking(employeeId, clockInTime) {
        if (!this.isSupported || !this.serviceWorker) {
            console.error('Background tracking not available');
            return false;
        }

        try {
            // Get current location status
            const statusResponse = await fetch('/employees/api/location-tracking-status/');
            const statusData = await statusResponse.json();

            if (!statusData.is_clocked_in) {
                console.log('Employee not clocked in, cannot start background tracking');
                return false;
            }

            const config = {
                employeeId: employeeId,
                clockInTime: clockInTime,
                lastLocationTime: statusData.last_log_time,
                startTime: new Date().toISOString()
            };

            // Send message to service worker to start tracking
            this.sendMessageToServiceWorker('START_BACKGROUND_TRACKING', config);

            this.isActive = true;

            // Show user notification
            this.showTrackingStartedNotification();

            console.log('Background location tracking started');
            return true;

        } catch (error) {
            console.error('Failed to start background tracking:', error);
            return false;
        }
    }

    // Stop background location tracking
    async stopTracking() {
        if (!this.serviceWorker) return;

        try {
            // Send message to service worker to stop tracking
            this.sendMessageToServiceWorker('STOP_BACKGROUND_TRACKING');

            this.isActive = false;

            console.log('Background location tracking stopped');

        } catch (error) {
            console.error('Failed to stop background tracking:', error);
        }
    }

    // Send message to service worker
    sendMessageToServiceWorker(type, data = null) {
        if (this.serviceWorker && this.serviceWorker.active) {
            this.serviceWorker.active.postMessage({ type, data });
        }
    }

    // Handle messages from service worker
    handleServiceWorkerMessage(event) {
        const { type, data } = event.data;

        switch (type) {
            case 'LOCATION_UPDATED':
                console.log('Location updated in background:', data);
                this.showLocationUpdateNotification();
                break;
            case 'TRACKING_ERROR':
                console.error('Background tracking error:', data);
                break;
            case 'TRACKING_STOPPED':
                console.log('Background tracking stopped by service worker');
                this.isActive = false;
                break;
        }
    }

    // Show notification when tracking starts
    showTrackingStartedNotification() {
        if (Notification.permission === 'granted') {
            new Notification('Background Location Tracking Started', {
                body: 'Your location will be automatically tracked every hour while you are clocked in.',
                icon: '/static/img/petabytz_logo.jpg',
                tag: 'tracking-started',
                requireInteraction: false
            });
        }
    }

    // Show notification when location is updated
    showLocationUpdateNotification() {
        if (Notification.permission === 'granted') {
            new Notification('Location Updated', {
                body: 'Your location has been automatically recorded for attendance tracking.',
                icon: '/static/img/petabytz_logo.jpg',
                tag: 'location-updated',
                requireInteraction: false
            });
        }
    }

    // Check if tracking should be active
    async checkTrackingStatus() {
        try {
            const response = await fetch('/employees/api/location-tracking-status/');
            const data = await response.json();

            if (data.is_clocked_in && !data.tracking_stopped) {
                if (!this.isActive) {
                    // Should be tracking but isn't - restart
                    await this.startTracking(data.employee_id, data.clock_in_time);
                }
            } else {
                if (this.isActive) {
                    // Should not be tracking but is - stop
                    await this.stopTracking();
                }
            }

            return data;

        } catch (error) {
            console.error('Failed to check tracking status:', error);
            return null;
        }
    }

    // Manual location sync
    async syncLocationNow() {
        if (this.serviceWorker) {
            this.sendMessageToServiceWorker('SYNC_LOCATION_NOW');
        }
    }

    // Get tracking status
    getStatus() {
        return {
            isSupported: this.isSupported,
            isActive: this.isActive,
            hasServiceWorker: !!this.serviceWorker
        };
    }
}

// Global instance
window.backgroundLocationTracker = new BackgroundLocationTracker();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    const tracker = window.backgroundLocationTracker;
    
    // Initialize the tracker
    const initialized = await tracker.initialize();
    
    if (initialized) {
        console.log('Background location tracker initialized successfully');
        
        // Check if we should start tracking
        const status = await tracker.checkTrackingStatus();
        
        if (status && status.is_clocked_in && !status.tracking_stopped) {
            await tracker.startTracking(status.employee_id, status.clock_in_time);
        }
        
        // Set up periodic status checks (every 5 minutes)
        setInterval(() => {
            tracker.checkTrackingStatus();
        }, 5 * 60 * 1000);
        
    } else {
        console.warn('Background location tracker could not be initialized');
    }
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible - check tracking status
        if (window.backgroundLocationTracker) {
            window.backgroundLocationTracker.checkTrackingStatus();
        }
    }
});

// Handle before unload
window.addEventListener('beforeunload', function() {
    // Don't stop tracking when page unloads - that's the point of background tracking!
    console.log('Page unloading, background tracking will continue...');
});

// Expose functions for manual control
window.startBackgroundLocationTracking = function(employeeId, clockInTime) {
    if (window.backgroundLocationTracker) {
        return window.backgroundLocationTracker.startTracking(employeeId, clockInTime);
    }
    return false;
};

window.stopBackgroundLocationTracking = function() {
    if (window.backgroundLocationTracker) {
        return window.backgroundLocationTracker.stopTracking();
    }
};

window.syncLocationNow = function() {
    if (window.backgroundLocationTracker) {
        return window.backgroundLocationTracker.syncLocationNow();
    }
};

window.getLocationTrackingStatus = function() {
    if (window.backgroundLocationTracker) {
        return window.backgroundLocationTracker.getStatus();
    }
    return { isSupported: false, isActive: false, hasServiceWorker: false };
};