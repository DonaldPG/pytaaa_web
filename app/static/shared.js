/**
 * PyTAAA Web - Shared JavaScript
 * Common constants and utilities for all dashboard pages
 */

// API Configuration
const API_BASE = '/api/v1';

// Model Colors - Official color scheme
const COLORS = {
    naz100_pine: 'rgb(0, 123, 220)',
    naz100_hma: 'rgb(220, 0, 0)',
    naz100_pi: 'rgb(0, 220, 0)',
    sp500_hma: 'rgb(0, 206, 209)',
    sp500_pine: 'rgb(250, 0, 250)',
    naz100_sp500_abacus: 'rgb(25, 25, 25)',
    CASH: 'rgb(25, 25, 25)'
};

// Period Options
const PERIOD_OPTIONS = [
    { value: 30, label: '1 month' },
    { value: 90, label: '3 months' },
    { value: 180, label: '6 months' },
    { value: 'ytd', label: 'YTD' },
    { value: 365, label: '1 year' },
    { value: 730, label: '2 years' },
    { value: 1095, label: '3 years' },
    { value: 1825, label: '5 years' },
    { value: 3650, label: '10 years' },
    { value: 100000, label: 'max' }
];

// Chart.js Defaults
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            display: false
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                maxTicksLimit: 12
            }
        },
        y: {
            beginAtZero: false,
            ticks: {
                callback: function(value) {
                    return '$' + value.toLocaleString();
                }
            }
        }
    }
};

// Utility Functions

/**
 * Format a number as currency
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

/**
 * Format a date string
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Get days from year start (for YTD calculations)
 */
function getDaysFromYTD() {
    const now = new Date();
    const startOfYear = new Date(now.getFullYear(), 0, 1);
    const diffTime = Math.abs(now - startOfYear);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Get the actual days value for a period option
 */
function getPeriodDays(periodValue) {
    if (periodValue === 'ytd') {
        return getDaysFromYTD();
    }
    return parseInt(periodValue);
}

/**
 * Show loading state
 */
function showLoading(container) {
    container.innerHTML = '<div class="loading">Loading...</div>';
}

/**
 * Show error state
 */
function showError(container, message) {
    container.innerHTML = `<div class="error">${message}</div>`;
}

/**
 * Create a period selector dropdown
 */
function createPeriodSelector(onChange, defaultValue = 90) {
    const select = document.createElement('select');
    select.className = 'period-select';
    
    PERIOD_OPTIONS.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.label;
        if (option.value === defaultValue) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
    
    select.addEventListener('change', (e) => {
        onChange(getPeriodDays(e.target.value));
    });
    
    return select;
}

/**
 * Fetch JSON from API with error handling
 */
async function fetchJSON(url) {
    const response = await fetch(url);
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

// Export for modules (if using ES modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        API_BASE,
        COLORS,
        PERIOD_OPTIONS,
        CHART_DEFAULTS,
        formatCurrency,
        formatDate,
        getDaysFromYTD,
        getPeriodDays,
        showLoading,
        showError,
        createPeriodSelector,
        fetchJSON
    };
}
