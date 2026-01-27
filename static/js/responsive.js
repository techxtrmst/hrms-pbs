/* Enhanced Mobile Navigation JavaScript for HRMS */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile navigation
    initializeMobileNavigation();
    
    // Initialize responsive features
    initializeResponsiveFeatures();
    
    // Initialize touch optimizations
    initializeTouchOptimizations();
    
    // Fix viewport height issues
    fixViewportHeight();
});

function initializeMobileNavigation() {
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const body = document.body;
    
    if (!mobileToggle || !sidebar || !overlay) {
        console.warn('Mobile navigation elements not found:', {
            mobileToggle: !!mobileToggle,
            sidebar: !!sidebar,
            overlay: !!overlay
        });
        return;
    }
    
    let isToggling = false; // Prevent rapid toggling
    let touchHandled = false; // Track if touch was handled
    
    function toggleSidebar(e) {
        if (isToggling) return; // Prevent multiple rapid clicks
        
        e.preventDefault();
        e.stopPropagation();
        
        isToggling = true;
        
        const isOpen = sidebar.classList.contains('show');
        
        if (isOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
        
        // Reset toggle flag after animation
        setTimeout(() => {
            isToggling = false;
            touchHandled = false;
        }, 400);
    }
    
    function openSidebar() {
        sidebar.classList.add('show');
        overlay.classList.add('show');
        body.classList.add('sidebar-open');
        
        // Update button icon
        const icon = mobileToggle.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-times';
        }
        
        mobileToggle.setAttribute('aria-expanded', 'true');
        
        // Prevent background scrolling
        const scrollY = window.scrollY;
        body.style.position = 'fixed';
        body.style.top = `-${scrollY}px`;
        body.style.width = '100%';
    }
    
    function closeSidebar() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
        body.classList.remove('sidebar-open');
        
        // Update button icon
        const icon = mobileToggle.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-bars';
        }
        
        mobileToggle.setAttribute('aria-expanded', 'false');
        
        // Restore scrolling
        const scrollY = body.style.top;
        body.style.position = '';
        body.style.top = '';
        body.style.width = '';
        if (scrollY) {
            window.scrollTo(0, parseInt(scrollY || '0') * -1);
        }
    }
    
    // Handle touch events first (for mobile)
    mobileToggle.addEventListener('touchstart', function(e) {
        if (isToggling) return;
        touchHandled = true;
        toggleSidebar(e);
    }, { passive: false });
    
    // Handle click events (for desktop and as fallback)
    mobileToggle.addEventListener('click', function(e) {
        if (touchHandled || isToggling) {
            touchHandled = false;
            return;
        }
        toggleSidebar(e);
    });
    
    overlay.addEventListener('click', function(e) {
        if (!isToggling) {
            e.preventDefault();
            e.stopPropagation();
            closeSidebar();
        }
    });
    
    // Close sidebar when clicking on a link (mobile only)
    const sidebarLinks = sidebar.querySelectorAll('a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Don't close sidebar if it's a dropdown toggle
            if (link.hasAttribute('data-bs-toggle') || 
                link.classList.contains('sidebar-dropdown-toggle') ||
                link.getAttribute('href') === '#' ||
                link.getAttribute('href')?.startsWith('#menu')) {
                // This is a dropdown toggle, don't close sidebar
                return;
            }
            
            // Only close sidebar for actual navigation links
            if (window.innerWidth <= 768 && sidebar.classList.contains('show')) {
                setTimeout(closeSidebar, 150); // Small delay for better UX
            }
        });
    });
    
    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (window.innerWidth > 768) {
                closeSidebar();
            }
        }, 250);
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('show') && !isToggling) {
            closeSidebar();
        }
    });
    
    // Prevent Bootstrap collapse events from closing the sidebar
    sidebar.addEventListener('click', function(e) {
        // If clicking on a collapse toggle, prevent sidebar from closing
        const target = e.target.closest('[data-bs-toggle="collapse"]');
        if (target) {
            e.stopPropagation();
        }
    });
    
    // Handle Bootstrap collapse events
    sidebar.addEventListener('show.bs.collapse', function(e) {
        e.stopPropagation();
    });
    
    sidebar.addEventListener('hide.bs.collapse', function(e) {
        e.stopPropagation();
    });
    
    // Prevent scrolling issues on mobile
    sidebar.addEventListener('touchmove', function(e) {
        e.stopPropagation();
    }, { passive: true });
    
    // Handle orientation change
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            if (sidebar.classList.contains('show')) {
                closeSidebar();
            }
            fixViewportHeight();
        }, 100);
    });
    
    // Mark that responsive.js handled the mobile navigation
    mobileToggle.setAttribute('data-responsive-handled', 'true');
}

function initializeResponsiveFeatures() {
    // Responsive table handling
    handleResponsiveTables();
    
    // Responsive modals
    handleResponsiveModals();
    
    // Responsive forms
    handleResponsiveForms();
    
    // Responsive charts (if any)
    handleResponsiveCharts();
}

function handleResponsiveTables() {
    const tables = document.querySelectorAll('.table-responsive');
    
    tables.forEach(tableContainer => {
        const table = tableContainer.querySelector('table');
        if (!table) return;
        
        // Add swipe indicator for mobile
        if (window.innerWidth <= 768) {
            // Check if indicator already exists
            if (!tableContainer.querySelector('.table-swipe-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'table-swipe-indicator';
                indicator.innerHTML = '<i class="fas fa-arrows-alt-h"></i> Swipe to see more';
                indicator.style.cssText = `
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(99, 102, 241, 0.1);
                    color: #6366f1;
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 0.75rem;
                    z-index: 10;
                    pointer-events: none;
                    opacity: 1;
                    transition: opacity 0.3s ease;
                `;
                
                tableContainer.style.position = 'relative';
                tableContainer.appendChild(indicator);
                
                // Hide indicator after scroll
                let scrollTimeout;
                tableContainer.addEventListener('scroll', () => {
                    indicator.style.opacity = '0.5';
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(() => {
                        indicator.style.opacity = '1';
                    }, 1000);
                });
                
                // Auto-hide after 3 seconds
                setTimeout(() => {
                    indicator.style.opacity = '0.7';
                }, 3000);
                
                // Add touch feedback to table rows
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    row.addEventListener('touchstart', function() {
                        this.style.backgroundColor = 'rgba(99, 102, 241, 0.05)';
                    }, { passive: true });
                    
                    row.addEventListener('touchend', function() {
                        setTimeout(() => {
                            this.style.backgroundColor = '';
                        }, 150);
                    }, { passive: true });
                    
                    row.addEventListener('touchcancel', function() {
                        this.style.backgroundColor = '';
                    }, { passive: true });
                });
            }
        }
        
        // Add horizontal scroll momentum for better mobile experience
        if ('ontouchstart' in window) {
            tableContainer.style.webkitOverflowScrolling = 'touch';
            tableContainer.style.overflowX = 'auto';
            
            // Prevent vertical scroll when scrolling table horizontally
            let isScrollingHorizontally = false;
            let startX, startY;
            
            tableContainer.addEventListener('touchstart', function(e) {
                startX = e.touches[0].pageX;
                startY = e.touches[0].pageY;
                isScrollingHorizontally = false;
            }, { passive: true });
            
            tableContainer.addEventListener('touchmove', function(e) {
                if (!startX || !startY) return;
                
                const diffX = Math.abs(e.touches[0].pageX - startX);
                const diffY = Math.abs(e.touches[0].pageY - startY);
                
                if (diffX > diffY && diffX > 10) {
                    isScrollingHorizontally = true;
                    e.stopPropagation();
                }
            }, { passive: false });
            
            tableContainer.addEventListener('touchend', function() {
                startX = null;
                startY = null;
                isScrollingHorizontally = false;
            }, { passive: true });
        }
    });
}

function handleResponsiveModals() {
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            // Adjust modal height on mobile
            if (window.innerWidth <= 768) {
                const modalDialog = modal.querySelector('.modal-dialog');
                const modalContent = modal.querySelector('.modal-content');
                
                if (modalDialog && modalContent) {
                    const maxHeight = window.innerHeight - 40;
                    modalContent.style.maxHeight = maxHeight + 'px';
                    modalContent.style.overflowY = 'auto';
                    modalContent.style.webkitOverflowScrolling = 'touch';
                }
            }
        });
        
        // Fix modal backdrop issues on mobile
        modal.addEventListener('show.bs.modal', function() {
            if (window.innerWidth <= 768) {
                document.body.style.paddingRight = '0px';
            }
        });
    });
}

function handleResponsiveForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Prevent zoom on iOS
            if (input.type !== 'file' && input.type !== 'range') {
                if (parseFloat(getComputedStyle(input).fontSize) < 16) {
                    input.style.fontSize = '16px';
                }
            }
            
            // Add touch-friendly styling
            if ('ontouchstart' in window) {
                input.style.minHeight = '44px';
                
                // Handle focus events for better mobile experience
                input.addEventListener('focus', function() {
                    // Scroll input into view on mobile
                    if (window.innerWidth <= 768) {
                        setTimeout(() => {
                            this.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }, 300);
                    }
                });
            }
        });
    });
}

function handleResponsiveCharts() {
    // Handle Chart.js responsive behavior
    if (typeof Chart !== 'undefined') {
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
    }
    
    // Handle other chart libraries
    const chartContainers = document.querySelectorAll('.chart-container, [id*="chart"], [class*="chart"]');
    
    chartContainers.forEach(container => {
        if (window.innerWidth <= 768) {
            container.style.height = '250px';
        } else if (window.innerWidth <= 576) {
            container.style.height = '200px';
        }
    });
}

function initializeTouchOptimizations() {
    if (!('ontouchstart' in window)) return;
    
    // Add touch class to body
    document.body.classList.add('touch-device');
    
    // Improve button touch targets
    const buttons = document.querySelectorAll('.btn, button, .nav-link, .dropdown-item');
    buttons.forEach(btn => {
        if (btn.offsetHeight < 44) {
            btn.style.minHeight = '44px';
            btn.style.display = 'flex';
            btn.style.alignItems = 'center';
        }
        
        // Remove tap highlight
        btn.style.webkitTapHighlightColor = 'transparent';
        btn.style.touchAction = 'manipulation';
    });
    
    // Improve table scrolling
    const scrollableElements = document.querySelectorAll('.table-responsive, .overflow-auto, .overflow-scroll');
    scrollableElements.forEach(element => {
        element.style.webkitOverflowScrolling = 'touch';
    });
    
    // Add touch feedback to interactive elements
    const interactiveElements = document.querySelectorAll('.btn, .card, .nav-link, .list-group-item');
    
    interactiveElements.forEach(element => {
        element.addEventListener('touchstart', function() {
            this.style.opacity = '0.8';
        }, { passive: true });
        
        element.addEventListener('touchend', function() {
            setTimeout(() => {
                this.style.opacity = '';
            }, 150);
        }, { passive: true });
        
        element.addEventListener('touchcancel', function() {
            this.style.opacity = '';
        }, { passive: true });
    });
    
    // Handle pull-to-refresh prevention where needed
    let startY = 0;
    document.addEventListener('touchstart', function(e) {
        startY = e.touches[0].pageY;
    }, { passive: true });
    
    document.addEventListener('touchmove', function(e) {
        const y = e.touches[0].pageY;
        const scrollableParent = findScrollableParent(e.target);
        
        if (scrollableParent && scrollableParent.scrollTop === 0 && y > startY) {
            // Allow pull-to-refresh
            return;
        }
        
        // Prevent overscroll
        if (window.pageYOffset === 0 && y > startY) {
            e.preventDefault();
        }
    }, { passive: false });
}

function findScrollableParent(element) {
    if (!element || element === document.body) return null;
    
    const overflowY = getComputedStyle(element).overflowY;
    if (overflowY === 'scroll' || overflowY === 'auto') {
        return element;
    }
    
    return findScrollableParent(element.parentElement);
}

function fixViewportHeight() {
    // Fix iOS viewport height issues
    function setViewportHeight() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }
    
    setViewportHeight();
    
    window.addEventListener('resize', setViewportHeight);
    window.addEventListener('orientationchange', function() {
        setTimeout(setViewportHeight, 100);
    });
}

// Utility functions for responsive behavior
window.ResponsiveUtils = {
    isMobile: () => window.innerWidth <= 768,
    isTablet: () => window.innerWidth > 768 && window.innerWidth <= 992,
    isDesktop: () => window.innerWidth > 992,
    isTouchDevice: () => 'ontouchstart' in window,
    
    // Debounced resize handler
    onResize: function(callback, delay = 250) {
        let timeout;
        window.addEventListener('resize', () => {
            clearTimeout(timeout);
            timeout = setTimeout(callback, delay);
        });
    },
    
    // Viewport height fix for mobile browsers
    setViewportHeight: function() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    },
    
    // Check if element is in viewport
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },
    
    // Smooth scroll to element
    scrollToElement: function(element, offset = 0) {
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
};

// Performance optimization: Reduce animations on low-end devices
if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
    document.documentElement.style.setProperty('--animation-duration', '0.1s');
    document.documentElement.style.setProperty('--transition-duration', '0.1s');
}

// Handle visibility change for better performance
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        // Re-initialize responsive features when page becomes visible
        setTimeout(() => {
            handleResponsiveTables();
            fixViewportHeight();
        }, 100);
    }
});

// Debug helper for mobile development
if (window.location.search.includes('debug=mobile')) {
    console.log('Mobile Debug Mode Enabled');
    
    // Show viewport dimensions
    function showViewportInfo() {
        const info = document.getElementById('viewport-info') || document.createElement('div');
        info.id = 'viewport-info';
        info.style.cssText = `
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 9999;
            pointer-events: none;
        `;
        info.innerHTML = `
            Viewport: ${window.innerWidth}x${window.innerHeight}<br>
            Device Pixel Ratio: ${window.devicePixelRatio}<br>
            Touch: ${ResponsiveUtils.isTouchDevice() ? 'Yes' : 'No'}<br>
            Mobile: ${ResponsiveUtils.isMobile() ? 'Yes' : 'No'}
        `;
        
        if (!document.getElementById('viewport-info')) {
            document.body.appendChild(info);
        }
    }
    
    showViewportInfo();
    window.addEventListener('resize', showViewportInfo);
    window.addEventListener('orientationchange', showViewportInfo);
}