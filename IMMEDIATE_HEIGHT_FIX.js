// Immediate Height Fix for Sidebar Spacing Issue
// Copy and paste this entire script in browser console (F12 → Console)

(function() {
    console.log('🔧 Starting immediate height fix for sidebar...');
    
    // Wait for DOM to be ready
    function fixSidebarHeights() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) {
            console.error('❌ Sidebar not found!');
            return;
        }
        
        console.log('✅ Sidebar found, applying fixes...');
        
        let fixedElements = 0;
        
        // 1. Fix any elements with 250px height to 20px
        const allElements = sidebar.querySelectorAll('*');
        allElements.forEach(element => {
            const computedStyle = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            
            // Check for 250px height
            if (computedStyle.height === '250px' || 
                element.style.height === '250px' || 
                rect.height === 250) {
                
                console.log('🎯 Found 250px element, fixing to 20px:', element);
                element.style.height = '20px';
                element.style.maxHeight = '20px';
                element.style.minHeight = '20px';
                fixedElements++;
            }
            
            // Check for any excessive heights
            if (rect.height > 100 && 
                !element.classList.contains('sidebar') && 
                !element.classList.contains('show')) {
                
                const hasContent = element.textContent.trim().length > 0;
                const isVisible = computedStyle.display !== 'none';
                
                if (!hasContent && isVisible) {
                    console.log('🔧 Fixing excessive height element:', element);
                    element.style.height = '20px';
                    element.style.maxHeight = '20px';
                    fixedElements++;
                }
            }
        });
        
        // 2. Completely hide collapsed sections
        const collapsedSections = sidebar.querySelectorAll('.collapse:not(.show)');
        collapsedSections.forEach(section => {
            section.style.display = 'none';
            section.style.height = '0px';
            section.style.maxHeight = '0px';
            section.style.minHeight = '0px';
            section.style.visibility = 'hidden';
            section.style.position = 'absolute';
            section.style.left = '-9999px';
            section.style.opacity = '0';
            
            console.log('🚫 Hidden collapsed section:', section.id || section.className);
        });
        
        // 3. Reset all margins and excessive spacing
        const sidebarChildren = sidebar.children;
        Array.from(sidebarChildren).forEach(child => {
            if (!child.classList.contains('collapse') || child.classList.contains('show')) {
                child.style.marginTop = '0px';
                child.style.marginBottom = '0px';
                
                // Limit height for non-expanded sections
                if (!child.classList.contains('show')) {
                    const currentHeight = child.getBoundingClientRect().height;
                    if (currentHeight > 60) {
                        child.style.maxHeight = '50px';
                    }
                }
            }
        });
        
        // 4. Add visual separators instead of spacing
        const visibleLinks = sidebar.querySelectorAll('a:not(.collapse a)');
        visibleLinks.forEach(link => {
            if (!link.closest('.collapse:not(.show)')) {
                link.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                link.style.margin = '0';
                link.style.padding = '10px 24px';
            }
        });
        
        console.log(`✅ Fixed ${fixedElements} elements with height issues`);
        console.log(`🚫 Hidden ${collapsedSections.length} collapsed sections`);
        console.log('🎉 Height fix complete! Check sidebar spacing now.');
        
        // 5. Force a repaint
        sidebar.style.display = 'none';
        sidebar.offsetHeight; // Trigger reflow
        sidebar.style.display = '';
        
        return {
            fixedElements,
            hiddenSections: collapsedSections.length,
            success: true
        };
    }
    
    // Run the fix
    const result = fixSidebarHeights();
    
    if (result && result.success) {
        console.log('🎯 SUCCESS: Sidebar height fix applied!');
        console.log('📱 The sidebar should now have proper spacing with 20px height for problematic elements.');
    }
    
    // Also add a mutation observer to catch any dynamic changes
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    const element = mutation.target;
                    if (element.style.height === '250px') {
                        console.log('🔄 Caught dynamic 250px height, fixing...');
                        element.style.height = '20px';
                        element.style.maxHeight = '20px';
                    }
                }
            });
        });
        
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            observer.observe(sidebar, {
                attributes: true,
                subtree: true,
                attributeFilter: ['style']
            });
            console.log('👀 Monitoring for dynamic height changes...');
        }
    }
    
})();

// Additional CSS injection for permanent fix
(function() {
    const style = document.createElement('style');
    style.innerHTML = `
        /* Immediate height fixes */
        .sidebar [style*="height: 250px"],
        .sidebar [style*="height:250px"] {
            height: 20px !important;
            max-height: 20px !important;
            min-height: 20px !important;
        }
        
        @media (max-width: 768px) {
            .sidebar > *:not(.collapse.show) {
                max-height: 50px !important;
            }
            
            .sidebar .collapse:not(.show) {
                display: none !important;
                height: 0 !important;
                max-height: 0 !important;
                position: absolute !important;
                left: -9999px !important;
            }
            
            .sidebar a {
                margin: 0 !important;
                padding: 10px 24px !important;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
        }
    `;
    document.head.appendChild(style);
    console.log('💉 Injected permanent CSS fixes');
})();