/**
 * Enhanced Responsive JavaScript for Employee Profile
 * Ultra-flexible design for all devices
 */

(function() {
    'use strict';
    
    // Enhanced responsive behavior initialization
    function initEnhancedResponsiveBehavior() {
        // Handle viewport height for mobile browsers with dynamic viewport
        function setVH() {
            let vh = window.innerHeight * 0.01;
            document.documentElement.style.setProperty('--vh', `${vh}px`);
        }
        
        setVH();
        window.addEventListener('resize', debounce(setVH, 100));
        window.addEventListener('orientationchange', () => {
            setTimeout(setVH, 100);
        });
        
        // Enhanced touch feedback for mobile devices
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
            document.body.classList.add('touch-device');
            initTouchFeedback();
        }
        
        // Initialize responsive navigation
        initResponsiveNavigation();
        
        // Initialize responsive grids
        initResponsiveGrids();
        
        // Initialize responsive cards
        initResponsiveCards();
        
        // Initialize responsive forms
        initResponsiveForms();
        
        // Initialize responsive images
        initResponsiveImages();
        
        // Initialize container queries polyfill for older browsers
        initContainerQueriesPolyfill();
        
        // Initialize intersection observer for performance
        initIntersectionObserver();
        
        // Initialize resize observer for dynamic layouts
        initResizeObserver();
    }
    
    // Enhanced touch feedback system
    function initTouchFeedback() {
        const touchElements = document.querySelectorAll('.camera-btn, .nav-link, .btn, .doc-upload-box, .info-group, .address-box');
        
        touchElements.forEach(element => {
            element.addEventListener('touchstart', function(e) {
                this.classList.add('touch-active');
                
                // Add haptic feedback if supported
                if (navigator.vibrate) {
                    navigator.vibrate(10);
                }
            }, { passive: true });
            
            element.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 150);
            }, { passive: true });
            
            element.addEventListener('touchcancel', function() {
                this.classList.remove('touch-active');
            }, { passive: true });
        });
    }
    
    // Enhanced responsive navigation
    function initResponsiveNavigation() {
        const navContainer = document.querySelector('.nav-container');
        const navPills = document.querySelector('.nav-pills-custom');
        
        if (!navPills) return;
        
        function updateNavigationLayout() {
            const containerWidth = navContainer ? navContainer.offsetWidth : window.innerWidth;
            const navLinks = navPills.querySelectorAll('.nav-link');
            const totalNavWidth = Array.from(navLinks).reduce((total, link) => {
                return total + link.offsetWidth + 8; // 8px for gap
            }, 0);
            
            // Dynamic navigation layout based on available space
            if (containerWidth < 400 || totalNavWidth > containerWidth) {
                navPills.classList.add('nav-stacked');
            } else {
                navPills.classList.remove('nav-stacked');
            }
            
            // Add scroll indicators if needed
            if (navPills.scrollWidth > navPills.clientWidth) {
                navPills.classList.add('nav-scrollable');
                addScrollIndicators(navPills);
            } else {
                navPills.classList.remove('nav-scrollable');
                removeScrollIndicators(navPills);
            }
        }
        
        updateNavigationLayout();
        window.addEventListener('resize', debounce(updateNavigationLayout, 150));
    }
    
    // Enhanced responsive grids with dynamic adjustment
    function initResponsiveGrids() {
        const grids = document.querySelectorAll('.content-area, .card-grid, .info-grid, .address-grid, .doc-grid, .contacts-grid, .form-grid, .form-grid-2');
        
        grids.forEach(grid => {
            // Ensure proper box-sizing and overflow handling
            grid.style.boxSizing = 'border-box';
            grid.style.maxWidth = '100%';
            grid.style.overflow = 'hidden';
            
            // Dynamic grid adjustment based on container width
            function adjustGrid() {
                const containerWidth = grid.offsetWidth;
                const children = grid.children;
                
                // Remove existing responsive classes
                grid.classList.remove('grid-single-column', 'grid-two-columns', 'grid-auto');
                
                // Determine optimal grid layout
                if (containerWidth < 320) {
                    grid.classList.add('grid-single-column');
                    grid.style.gridTemplateColumns = '1fr';
                    grid.style.gap = '0.25rem';
                } else if (containerWidth < 400) {
                    grid.classList.add('grid-single-column');
                    grid.style.gridTemplateColumns = '1fr';
                    grid.style.gap = '0.5rem';
                } else if (containerWidth < 600) {
                    // Allow natural grid behavior for small screens
                    grid.classList.add('grid-two-columns');
                    grid.style.gridTemplateColumns = '';
                    grid.style.gap = '';
                } else {
                    // Reset to CSS-defined behavior
                    grid.classList.add('grid-auto');
                    grid.style.gridTemplateColumns = '';
                    grid.style.gap = '';
                }
                
                // Ensure all child elements don't overflow
                Array.from(children).forEach(child => {
                    child.style.minWidth = '0';
                    child.style.maxWidth = '100%';
                    child.style.boxSizing = 'border-box';
                });
            }
            
            adjustGrid();
            window.addEventListener('resize', debounce(adjustGrid, 150));
        });
    }
    
    // Enhanced responsive cards with dynamic height adjustment
    function initResponsiveCards() {
        const cardGrids = document.querySelectorAll('.card-grid');
        
        function equalizeCardHeights() {
            cardGrids.forEach(grid => {
                const cards = grid.querySelectorAll('.content-card');
                
                // Reset heights first
                cards.forEach(card => {
                    card.style.height = 'auto';
                });
                
                // Only equalize heights on larger screens
                if (window.innerWidth > 767) {
                    let maxHeight = 0;
                    
                    // Find max height
                    cards.forEach(card => {
                        const height = card.offsetHeight;
                        if (height > maxHeight) {
                            maxHeight = height;
                        }
                    });
                    
                    // Apply max height
                    cards.forEach(card => {
                        card.style.height = maxHeight + 'px';
                    });
                } else {
                    // On mobile, add responsive classes
                    cards.forEach(card => {
                        card.classList.add('mobile-card');
                    });
                }
            });
        }
        
        equalizeCardHeights();
        window.addEventListener('resize', debounce(equalizeCardHeights, 200));
    }
    
    // Enhanced responsive forms with validation
    function initResponsiveForms() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            // Enhanced mobile form validation
            form.addEventListener('submit', function(e) {
                const requiredFields = form.querySelectorAll('[required]');
                let isValid = true;
                let firstInvalidField = null;
                
                requiredFields.forEach(field => {
                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('is-invalid');
                        
                        if (!firstInvalidField) {
                            firstInvalidField = field;
                        }
                    } else {
                        field.classList.remove('is-invalid');
                    }
                });
                
                if (!isValid) {
                    e.preventDefault();
                    
                    // Scroll to first invalid field on mobile
                    if (window.innerWidth <= 767 && firstInvalidField) {
                        firstInvalidField.scrollIntoView({ 
                            behavior: 'smooth', 
                            block: 'center' 
                        });
                        
                        // Focus with delay to ensure scroll completes
                        setTimeout(() => {
                            firstInvalidField.focus();
                        }, 300);
                    }
                }
            });
            
            // Real-time validation feedback
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    if (this.hasAttribute('required') && !this.value.trim()) {
                        this.classList.add('is-invalid');
                    } else {
                        this.classList.remove('is-invalid');
                    }
                });
                
                input.addEventListener('input', function() {
                    if (this.classList.contains('is-invalid') && this.value.trim()) {
                        this.classList.remove('is-invalid');
                    }
                });
            });
        });
    }
    
    // Enhanced responsive images with lazy loading
    function initResponsiveImages() {
        const images = document.querySelectorAll('.profile-avatar, .doc-preview-img');
        
        images.forEach(img => {
            // Add loading state
            img.classList.add('loading');
            
            img.addEventListener('load', function() {
                this.classList.remove('loading');
                this.classList.add('loaded');
            });
            
            img.addEventListener('error', function() {
                this.classList.remove('loading');
                this.classList.add('error');
                
                // Add fallback behavior for profile avatars
                if (this.classList.contains('profile-avatar')) {
                    this.style.display = 'none';
                    const wrapper = this.closest('.profile-avatar-wrapper');
                    if (wrapper) {
                        const placeholder = wrapper.querySelector('.profile-avatar.placeholder');
                        if (placeholder) {
                            placeholder.style.display = 'flex';
                        }
                    }
                }
            });
        });
        
        // Implement lazy loading for images
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            observer.unobserve(img);
                        }
                    }
                });
            });
            
            const lazyImages = document.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => imageObserver.observe(img));
        }
    }
    
    // Container queries polyfill for older browsers
    function initContainerQueriesPolyfill() {
        if (!CSS.supports('container-type: inline-size')) {
            const containers = document.querySelectorAll('.profile-container, .content-area');
            
            containers.forEach(container => {
                function checkContainerSize() {
                    const width = container.offsetWidth;
                    
                    // Remove existing container classes
                    container.classList.remove('container-small', 'container-medium', 'container-large');
                    
                    // Add appropriate class based on width
                    if (width < 400) {
                        container.classList.add('container-small');
                    } else if (width < 800) {
                        container.classList.add('container-medium');
                    } else {
                        container.classList.add('container-large');
                    }
                }
                
                checkContainerSize();
                window.addEventListener('resize', debounce(checkContainerSize, 150));
            });
        }
    }
    
    // Intersection Observer for performance optimization
    function initIntersectionObserver() {
        if ('IntersectionObserver' in window) {
            const observerOptions = {
                root: null,
                rootMargin: '50px',
                threshold: 0.1
            };
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('in-viewport');
                        
                        // Trigger animations for elements entering viewport
                        if (entry.target.classList.contains('fade-in-up')) {
                            entry.target.style.animationPlayState = 'running';
                        }
                    } else {
                        entry.target.classList.remove('in-viewport');
                    }
                });
            }, observerOptions);
            
            // Observe all animated elements
            const animatedElements = document.querySelectorAll('.fade-in-up, .content-card, .info-group');
            animatedElements.forEach(el => observer.observe(el));
        }
    }
    
    // Resize Observer for dynamic layouts
    function initResizeObserver() {
        if ('ResizeObserver' in window) {
            const resizeObserver = new ResizeObserver(entries => {
                entries.forEach(entry => {
                    const element = entry.target;
                    const width = entry.contentRect.width;
                    
                    // Dynamic class assignment based on element width
                    element.classList.remove('element-small', 'element-medium', 'element-large');
                    
                    if (width < 300) {
                        element.classList.add('element-small');
                    } else if (width < 600) {
                        element.classList.add('element-medium');
                    } else {
                        element.classList.add('element-large');
                    }
                    
                    // Trigger custom resize event
                    element.dispatchEvent(new CustomEvent('elementResize', {
                        detail: { width: width, height: entry.contentRect.height }
                    }));
                });
            });
            
            // Observe key elements
            const observedElements = document.querySelectorAll('.profile-card-main, .content-area, .card-grid');
            observedElements.forEach(el => resizeObserver.observe(el));
        }
    }
    
    // Enhanced document preview with responsive handling
    function updateDocPreview(input) {
        if (input.files && input.files[0]) {
            const box = input.closest('.doc-upload-box');
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Hide existing content
                const placeholders = box.querySelectorAll('.text-muted, .doc-preview-img, .fw-bold.text-dark');
                placeholders.forEach(el => el.style.display = 'none');
                
                // Create responsive preview
                let existingPreview = box.querySelector('.temp-preview');
                if (!existingPreview) {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.className = 'doc-preview-img w-100 temp-preview';
                    img.style.maxWidth = '100%';
                    img.style.height = 'auto';
                    
                    const label = document.createElement('div');
                    label.className = 'fw-bold text-dark temp-label';
                    const nameMap = {
                        'aadhar_front': 'Aadhar Front',
                        'aadhar_back': 'Aadhar Back',
                        'pan_card': 'PAN Card'
                    };
                    label.innerText = nameMap[input.name] + ' (Selected)';
                    
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-info doc-status-badge';
                    badge.innerHTML = '<i class="fas fa-save"></i> Save Required';
                    
                    // Insert elements responsively
                    box.insertBefore(badge, input);
                    box.insertBefore(img, input);
                    box.insertBefore(label, input);
                } else {
                    existingPreview.src = e.target.result;
                }
            };
            
            reader.readAsDataURL(input.files[0]);
        }
    }
    
    // Scroll indicators for navigation
    function addScrollIndicators(element) {
        if (element.querySelector('.scroll-indicator')) return;
        
        const indicator = document.createElement('div');
        indicator.className = 'scroll-indicator';
        indicator.innerHTML = '→';
        indicator.style.cssText = `
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            background: linear-gradient(90deg, transparent 0%, rgba(99, 102, 241, 0.1) 50%, rgba(99, 102, 241, 0.2) 100%);
            color: #6366f1;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            pointer-events: none;
            opacity: 0.8;
            transition: opacity 0.3s ease;
            z-index: 10;
        `;
        
        element.style.position = 'relative';
        element.appendChild(indicator);
        
        // Hide indicator when scrolled
        element.addEventListener('scroll', function() {
            if (this.scrollLeft > 0) {
                indicator.style.opacity = '0';
            } else {
                indicator.style.opacity = '0.8';
            }
        });
    }
    
    function removeScrollIndicators(element) {
        const indicator = element.querySelector('.scroll-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Debounce utility function
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Throttle utility function
    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // Enhanced performance monitoring
    function initPerformanceMonitoring() {
        // Monitor layout shifts
        if ('LayoutShift' in window) {
            let cumulativeLayoutShift = 0;
            
            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (!entry.hadRecentInput) {
                        cumulativeLayoutShift += entry.value;
                    }
                }
            }).observe({ type: 'layout-shift', buffered: true });
        }
        
        // Monitor long tasks
        if ('PerformanceObserver' in window) {
            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.duration > 50) {
                        console.warn('Long task detected:', entry.duration + 'ms');
                    }
                }
            }).observe({ type: 'longtask', buffered: true });
        }
    }
    
    // Initialize everything when DOM is ready
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initEnhancedResponsiveBehavior);
        } else {
            initEnhancedResponsiveBehavior();
        }
        
        // Initialize performance monitoring in development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            initPerformanceMonitoring();
        }
        
        // Add loading states
        document.body.classList.add('page-loaded');
        
        // Handle orientation change with delay
        window.addEventListener('orientationchange', function() {
            setTimeout(() => {
                window.dispatchEvent(new Event('resize'));
                initEnhancedResponsiveBehavior();
            }, 100);
        });
        
        // Initialize flexible grid behavior
        initResponsiveGrids();
        
        // Handle dynamic content resizing
        handleDynamicResize();
    }
    
    // Handle dynamic content resizing
    function handleDynamicResize() {
        const resizeHandler = throttle(() => {
            // Recalculate grid layouts
            const grids = document.querySelectorAll('.content-area, .card-grid, .info-grid, .address-grid, .doc-grid, .contacts-grid');
            grids.forEach(grid => {
                // Force reflow to recalculate grid
                const display = grid.style.display;
                grid.style.display = 'none';
                grid.offsetHeight; // Trigger reflow
                grid.style.display = display || '';
                
                // Ensure proper sizing
                grid.style.maxWidth = '100%';
                grid.style.overflow = 'hidden';
            });
            
            // Update navigation layout
            initResponsiveNavigation();
            
            // Update card heights
            initResponsiveCards();
            
            // Force viewport recalculation on mobile
            if (window.innerWidth <= 768) {
                document.body.style.overflow = 'hidden';
                setTimeout(() => {
                    document.body.style.overflow = '';
                }, 10);
            }
        }, 150);
        
        window.addEventListener('resize', resizeHandler);
    }
    
    // Expose global functions
    window.updateDocPreview = updateDocPreview;
    window.initEnhancedResponsiveBehavior = initEnhancedResponsiveBehavior;
    
    // Initialize
    init();
    
})();

// Additional CSS classes for JavaScript-enhanced responsive behavior
document.documentElement.classList.add('js-enhanced');

// Detect device capabilities
if (window.matchMedia('(hover: hover)').matches) {
    document.documentElement.classList.add('hover-supported');
} else {
    document.documentElement.classList.add('touch-only');
}

// Detect high DPI displays
if (window.devicePixelRatio > 1) {
    document.documentElement.classList.add('high-dpi');
}

// Detect reduced motion preference
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.classList.add('reduced-motion');
}

// Detect dark mode preference
if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.classList.add('dark-mode');
}

// Detect high contrast preference
if (window.matchMedia('(prefers-contrast: high)').matches) {
    document.documentElement.classList.add('high-contrast');
}