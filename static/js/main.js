// static/js/main.js

// Global Variables
let currentAccount = null;
let loadingSpinner = null;

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    // Create loading spinner
    createLoadingSpinner();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Check for flash messages
    checkFlashMessages();
});

// Create loading spinner
function createLoadingSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-wrapper';
    spinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(spinner);
    loadingSpinner = spinner;
}

// Show loading spinner
function showLoading() {
    if (loadingSpinner) {
        loadingSpinner.style.display = 'flex';
    }
}

// Hide loading spinner
function hideLoading() {
    if (loadingSpinner) {
        loadingSpinner.style.display = 'none';
    }
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Check for flash messages
function checkFlashMessages() {
    const messages = document.querySelectorAll('.flash-message');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) { // Less than 1 minute
        return 'Baru saja';
    } else if (diff < 3600000) { // Less than 1 hour
        const minutes = Math.floor(diff / 60000);
        return `${minutes} menit yang lalu`;
    } else if (diff < 86400000) { // Less than 1 day
        const hours = Math.floor(diff / 3600000);
        return `${hours} jam yang lalu`;
    } else {
        return date.toLocaleDateString('id-ID', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Berhasil disalin!', 'success');
    }).catch(() => {
        showNotification('Gagal menyalin', 'error');
    });
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.animation = 'slideInRight 0.5s ease';
    notification.innerHTML = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease';
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 3000);
}

// Confirm action
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Export data to CSV
function exportToCSV(data, filename) {
    const csv = data.map(row => 
        Object.values(row).map(value => 
            typeof value === 'string' ? `"${value}"` : value
        ).join(',')
    ).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Debounce function
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

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// API Request wrapper
async function apiRequest(url, method = 'GET', data = null) {
    showLoading();
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data) {
        if (data instanceof FormData) {
            options.body = data;
            delete options.headers['Content-Type'];
        } else {
            options.body = JSON.stringify(data);
        }
    }
    
    try {
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Terjadi kesalahan');
        }
        
        return result;
    } catch (error) {
        showNotification(error.message, 'error');
        throw error;
    } finally {
        hideLoading();
    }
}

// Pagination handler
class Pagination {
    constructor(totalItems, itemsPerPage, onPageChange) {
        this.totalItems = totalItems;
        this.itemsPerPage = itemsPerPage;
        this.onPageChange = onPageChange;
        this.currentPage = 1;
        this.totalPages = Math.ceil(totalItems / itemsPerPage);
    }
    
    getVisiblePages() {
        const delta = 2;
        const range = [];
        const rangeWithDots = [];
        let l;
        
        for (let i = 1; i <= this.totalPages; i++) {
            if (i === 1 || i === this.totalPages || (i >= this.currentPage - delta && i <= this.currentPage + delta)) {
                range.push(i);
            }
        }
        
        range.forEach(i => {
            if (l) {
                if (i - l === 2) {
                    rangeWithDots.push(l + 1);
                } else if (i - l !== 1) {
                    rangeWithDots.push('...');
                }
            }
            rangeWithDots.push(i);
            l = i;
        });
        
        return rangeWithDots;
    }
    
    goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage) {
            return;
        }
        
        this.currentPage = page;
        this.onPageChange(page);
    }
    
    nextPage() {
        this.goToPage(this.currentPage + 1);
    }
    
    prevPage() {
        this.goToPage(this.currentPage - 1);
    }
}