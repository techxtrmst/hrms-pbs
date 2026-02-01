// Debug script for mobile navigation issues
// Add this to your page temporarily to debug the hamburger menu

console.log('🔍 Mobile Navigation Debug Script Loaded');

document.addEventListener('DOMContentLoaded', function() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    console.log('📱 Elements found:', {
        mobileToggle: !!mobileToggle,
        sidebar: !!sidebar,
        overlay: !!overlay
    });

    if (mobileToggle) {
        console.log('🔘 Mobile toggle button found');

        // Log all event listeners
        mobileToggle.addEventListener('click', function(e) {
            console.log('🖱️ Click event fired');
        });

        mobileToggle.addEventListener('touchstart', function(e) {
            console.log('👆 Touch start event fired');
        });

        mobileToggle.addEventListener('touchend', function(e) {
            console.log('👆 Touch end event fired');
        });

        // Monitor sidebar state changes
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const hasShow = sidebar.classList.contains('show');
                    console.log('📋 Sidebar state changed:', hasShow ? 'OPEN' : 'CLOSED');
                }
            });
        });

        if (sidebar) {
            observer.observe(sidebar, { attributes: true });
        }

        // Monitor rapid clicks
        let clickCount = 0;
        let clickTimer;

        mobileToggle.addEventListener('click', function() {
            clickCount++;
            clearTimeout(clickTimer);

            clickTimer = setTimeout(() => {
                if (clickCount > 1) {
                    console.warn('⚠️ Rapid clicks detected:', clickCount, 'clicks in 500ms');
                }
                clickCount = 0;
            }, 500);
        });
    } else {
        console.error('❌ Mobile toggle button not found!');
    }

    // Monitor viewport changes
    window.addEventListener('resize', function() {
        console.log('📐 Viewport changed:', window.innerWidth + 'x' + window.innerHeight);
    });

    // Monitor touch events globally
    document.addEventListener('touchstart', function(e) {
        console.log('👆 Global touch start on:', e.target.tagName, e.target.className);
    });
});

// Add visual indicator for debugging
function addDebugIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'debug-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: #ff4444;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 9999;
        pointer-events: none;
    `;
    indicator.textContent = 'DEBUG MODE';
    document.body.appendChild(indicator);
}

addDebugIndicator();

console.log('🚀 Debug script ready. Check console for mobile navigation events.');
