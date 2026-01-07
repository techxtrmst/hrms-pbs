/**
 * SuperAdmin Dashboard JavaScript
 * Handles company context switching, metric card interactions, and dynamic updates
 */

(function() {
    'use strict';

    // Company Context Management
    const CompanyContext = {
        init: function() {
            this.setupCompanySelector();
            this.setupMetricCardClicks();
            this.loadSavedContext();
        },

        setupCompanySelector: function() {
            const selector = document.getElementById('companySelectorDropdown');
            if (!selector) return;

            selector.addEventListener('change', (e) => {
                const companyId = e.target.value;
                this.switchCompany(companyId);
            });
        },

        switchCompany: function(companyId) {
            // Show loading state
            const selector = document.getElementById('companySelectorDropdown');
            if (selector) {
                selector.disabled = true;
            }

            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

            // Make AJAX request
            fetch('/superadmin/api/switch-company/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `company_id=${companyId}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Save to localStorage
                    if (companyId === 'null' || companyId === '') {
                        localStorage.removeItem('sa_selected_company');
                    } else {
                        localStorage.setItem('sa_selected_company', companyId);
                    }

                    // Show success message
                    this.showToast(data.message, 'success');

                    // Reload page to update metrics
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                } else {
                    this.showToast(data.message, 'error');
                    if (selector) selector.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error switching company:', error);
                this.showToast('Failed to switch company', 'error');
                if (selector) selector.disabled = false;
            });
        },

        loadSavedContext: function() {
            const savedCompany = localStorage.getItem('sa_selected_company');
            const selector = document.getElementById('companySelectorDropdown');
            
            if (savedCompany && selector) {
                selector.value = savedCompany;
            }
        },

        setupMetricCardClicks: function() {
            // Total Companies Card
            const companiesCard = document.querySelector('[data-metric="companies"]');
            if (companiesCard) {
                companiesCard.addEventListener('click', () => {
                    window.location.href = '/superadmin/companies/';
                });
            }

            // Total Employees Card
            const employeesCard = document.querySelector('[data-metric="employees"]');
            if (employeesCard) {
                employeesCard.addEventListener('click', () => {
                    const companyId = this.getCurrentCompanyId();
                    const url = companyId ? 
                        `/superadmin/employees/?company_id=${companyId}` : 
                        '/superadmin/employees/';
                    window.location.href = url;
                });
            }

            // Present Today Card
            const presentCard = document.querySelector('[data-metric="present"]');
            if (presentCard) {
                presentCard.addEventListener('click', () => {
                    const companyId = this.getCurrentCompanyId();
                    const url = companyId ? 
                        `/superadmin/attendance/today/?company_id=${companyId}` : 
                        '/superadmin/attendance/today/';
                    window.location.href = url;
                });
            }

            // On Leave Card
            const leaveCard = document.querySelector('[data-metric="leave"]');
            if (leaveCard) {
                leaveCard.addEventListener('click', () => {
                    const companyId = this.getCurrentCompanyId();
                    const url = companyId ? 
                        `/superadmin/leaves/today/?company_id=${companyId}` : 
                        '/superadmin/leaves/today/';
                    window.location.href = url;
                });
            }
        },

        getCurrentCompanyId: function() {
            const selector = document.getElementById('companySelectorDropdown');
            if (selector && selector.value && selector.value !== 'null') {
                return selector.value;
            }
            return null;
        },

        showToast: function(message, type = 'info') {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `sa-toast sa-toast-${type}`;
            toast.innerHTML = `
                <div class="sa-toast-content">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                    <span>${message}</span>
                </div>
            `;

            // Add to body
            document.body.appendChild(toast);

            // Show toast
            setTimeout(() => toast.classList.add('show'), 100);

            // Remove toast after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    };

    // Export Functionality
    const ExportManager = {
        init: function() {
            this.setupExportButtons();
        },

        setupExportButtons: function() {
            const exportButtons = document.querySelectorAll('[data-export]');
            exportButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    const reportType = button.dataset.export;
                    const companyId = CompanyContext.getCurrentCompanyId();
                    this.exportData(reportType, companyId);
                });
            });
        },

        exportData: function(reportType, companyId) {
            let url = `/superadmin/export/${reportType}/`;
            if (companyId) {
                url += `?company_id=${companyId}`;
            }

            // Show loading state
            CompanyContext.showToast('Preparing export...', 'info');

            // Trigger download
            window.location.href = url;
        }
    };

    // Chart Initialization (for company monitor dashboard)
    const ChartManager = {
        init: function() {
            this.initLeaveDistributionChart();
            this.initMonthlyTrendsChart();
            this.initAttendanceHeatmap();
        },

        initLeaveDistributionChart: function() {
            const canvas = document.getElementById('leaveDistributionChart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const data = JSON.parse(canvas.dataset.chartData || '[]');

            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(d => d.label),
                    datasets: [{
                        data: data.map(d => d.value),
                        backgroundColor: [
                            '#3b82f6',
                            '#10b981',
                            '#f59e0b',
                            '#ef4444',
                            '#8b5cf6'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: {
                                    size: 12,
                                    family: 'Inter, sans-serif'
                                }
                            }
                        }
                    }
                }
            });
        },

        initMonthlyTrendsChart: function() {
            const canvas = document.getElementById('monthlyTrendsChart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const data = JSON.parse(canvas.dataset.chartData || '[]');

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.month),
                    datasets: [{
                        label: 'Leave Requests',
                        data: data.map(d => d.count),
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: '#6366f1',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: '#e2e8f0'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        },

        initAttendanceHeatmap: function() {
            const container = document.getElementById('attendanceHeatmap');
            if (!container) return;

            const data = JSON.parse(container.dataset.heatmapData || '[]');
            
            // Render heatmap using custom implementation
            this.renderHeatmap(container, data);
        },

        renderHeatmap: function(container, data) {
            // Simple heatmap implementation
            const html = data.map(day => {
                const intensity = this.calculateIntensity(day.present_count, day.total_employees);
                const color = this.getHeatmapColor(intensity);
                
                return `
                    <div class="heatmap-cell" 
                         style="background-color: ${color}"
                         title="${day.date}: ${day.present_count}/${day.total_employees} present">
                        ${new Date(day.date).getDate()}
                    </div>
                `;
            }).join('');

            container.innerHTML = `<div class="heatmap-grid">${html}</div>`;
        },

        calculateIntensity: function(present, total) {
            if (total === 0) return 0;
            return present / total;
        },

        getHeatmapColor: function(intensity) {
            if (intensity >= 0.9) return '#10b981'; // Green
            if (intensity >= 0.75) return '#84cc16'; // Light green
            if (intensity >= 0.6) return '#fbbf24'; // Yellow
            if (intensity >= 0.4) return '#f97316'; // Orange
            return '#ef4444'; // Red
        }
    };

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        CompanyContext.init();
        ExportManager.init();
        
        // Initialize charts if Chart.js is loaded
        if (typeof Chart !== 'undefined') {
            ChartManager.init();
        }
    });

    // Expose to global scope if needed
    window.SuperAdminDashboard = {
        CompanyContext,
        ExportManager,
        ChartManager
    };

})();

// Toast Styles (injected dynamically)
const toastStyles = `
    .sa-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        opacity: 0;
        transform: translateX(400px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        min-width: 300px;
    }

    .sa-toast.show {
        opacity: 1;
        transform: translateX(0);
    }

    .sa-toast-content {
        display: flex;
        align-items: center;
        font-size: 0.9375rem;
        font-weight: 500;
    }

    .sa-toast-success {
        border-left: 4px solid #10b981;
        color: #059669;
    }

    .sa-toast-error {
        border-left: 4px solid #ef4444;
        color: #dc2626;
    }

    .sa-toast-info {
        border-left: 4px solid #6366f1;
        color: #4f46e5;
    }
`;

// Inject toast styles
const styleSheet = document.createElement('style');
styleSheet.textContent = toastStyles;
document.head.appendChild(styleSheet);
