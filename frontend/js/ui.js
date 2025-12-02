/**
 * OrgMeet UI Utilities
 *
 * Reusable UI helper functions for presentation, notifications, formatting, and DOM utilities.
 * These are pure UI concerns separated from business logic in app.js.
 */

const UI = {
    // ========================================
    // NOTIFICATIONS
    // ========================================

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of notification: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms before auto-hide (default: 3000)
     */
    showNotification(message, type = 'info', duration = 3000) {
        // Remove existing notifications
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            info: 'bg-blue-500',
            warning: 'bg-yellow-500'
        };

        const notification = document.createElement('div');
        notification.className = `notification fixed top-4 right-4 ${colors[type] || colors.info} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    },

    /**
     * Show a success notification (shorthand)
     */
    showSuccess(message) {
        this.showNotification(message, 'success');
    },

    /**
     * Show an error notification (shorthand)
     */
    showError(message) {
        this.showNotification(message, 'error');
    },

    // ========================================
    // DATE FORMATTING
    // ========================================

    /**
     * Format a date string for display with full details
     * @param {string|Date} dateStr - ISO date string or Date object
     * @returns {string} Formatted date string
     */
    formatDate(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * Format a date string as short date (no time)
     * @param {string|Date} dateStr - ISO date string or Date object
     * @returns {string} Formatted short date string
     */
    formatShortDate(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    },

    /**
     * Format a date string for datetime-local input
     * @param {string|Date} dateStr - ISO date string or Date object
     * @returns {string} YYYY-MM-DDTHH:MM format
     */
    formatDateTimeLocal(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toISOString().slice(0, 16);
    },

    /**
     * Format a date string for date input
     * @param {string|Date} dateStr - ISO date string or Date object
     * @returns {string} YYYY-MM-DD format
     */
    formatDateInput(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toISOString().slice(0, 10);
    },

    /**
     * Get relative time (e.g., "2 hours ago")
     * @param {string|Date} dateStr - ISO date string or Date object
     * @returns {string} Relative time string
     */
    formatRelativeTime(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
        return this.formatShortDate(dateStr);
    },

    // ========================================
    // STATUS & BADGES
    // ========================================

    /**
     * Get CSS class for status badge
     * @param {string} status - Status value
     * @returns {string} Tailwind CSS classes
     */
    getStatusBadgeClass(status) {
        const classes = {
            // General
            draft: 'bg-gray-100 text-gray-700',
            pending: 'bg-yellow-100 text-yellow-700',
            active: 'bg-green-100 text-green-700',
            inactive: 'bg-gray-100 text-gray-700',

            // Meeting statuses
            scheduled: 'bg-blue-100 text-blue-700',
            in_progress: 'bg-green-100 text-green-700',
            completed: 'bg-gray-100 text-gray-700',
            cancelled: 'bg-red-100 text-red-700',

            // Motion statuses
            submitted: 'bg-blue-100 text-blue-700',
            screening: 'bg-yellow-100 text-yellow-700',
            discussion: 'bg-yellow-100 text-yellow-700',
            voting: 'bg-purple-100 text-purple-700',
            accepted: 'bg-green-100 text-green-700',
            rejected: 'bg-red-100 text-red-700',
            withdrawn: 'bg-gray-100 text-gray-700',
            referred: 'bg-blue-100 text-blue-700',

            // Poll statuses
            open: 'bg-green-100 text-green-700',
            closed: 'bg-gray-100 text-gray-700',

            // Member statuses
            approved: 'bg-green-100 text-green-700',
            expired: 'bg-red-100 text-red-700',
            suspended: 'bg-orange-100 text-orange-700',

            // Donation/Finance
            received: 'bg-green-100 text-green-700',
            pledged: 'bg-blue-100 text-blue-700',
            posted: 'bg-green-100 text-green-700',
            voided: 'bg-red-100 text-red-700'
        };
        return classes[status?.toLowerCase()] || 'bg-gray-100 text-gray-700';
    },

    /**
     * Get CSS class for role badge
     * @param {string} role - Role value (owner, admin, member, viewer)
     * @returns {string} Tailwind CSS classes
     */
    getRoleBadgeClass(role) {
        const classes = {
            owner: 'bg-purple-100 text-purple-700',
            admin: 'bg-blue-100 text-blue-700',
            member: 'bg-green-100 text-green-700',
            viewer: 'bg-gray-100 text-gray-700'
        };
        return classes[role?.toLowerCase()] || 'bg-gray-100 text-gray-700';
    },

    /**
     * Render a status badge HTML
     * @param {string} status - Status value
     * @returns {string} HTML string
     */
    renderStatusBadge(status) {
        const displayStatus = status?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown';
        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${this.getStatusBadgeClass(status)}">${displayStatus}</span>`;
    },

    // ========================================
    // LIST RENDERING
    // ========================================

    /**
     * Show loading state in a container
     * @param {string|HTMLElement} container - Container element or ID
     * @param {string} type - 'table' or 'card'
     */
    showLoading(container, type = 'table') {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (!el) return;

        if (type === 'table') {
            el.innerHTML = '<tr><td colspan="100%" class="text-center py-4">Loading...</td></tr>';
        } else {
            el.innerHTML = '<div class="text-center py-4">Loading...</div>';
        }
    },

    /**
     * Show empty state in a container
     * @param {string|HTMLElement} container - Container element or ID
     * @param {string} message - Empty message to display
     * @param {string} type - 'table' or 'card'
     */
    showEmpty(container, message = 'No items found.', type = 'table') {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (!el) return;

        if (type === 'table') {
            el.innerHTML = `<tr><td colspan="100%" class="text-center py-4 text-muted">${message}</td></tr>`;
        } else {
            el.innerHTML = `<div class="text-center py-4 text-muted">${message}</div>`;
        }
    },

    /**
     * Show error state in a container
     * @param {string|HTMLElement} container - Container element or ID
     * @param {string} message - Error message to display
     * @param {string} type - 'table' or 'card'
     */
    showContainerError(container, message = 'Error loading data', type = 'table') {
        const el = typeof container === 'string' ? document.getElementById(container) : container;
        if (!el) return;

        if (type === 'table') {
            el.innerHTML = `<tr><td colspan="100%" class="text-center py-4 text-danger">${message}</td></tr>`;
        } else {
            el.innerHTML = `<div class="text-center py-4 text-danger">${message}</div>`;
        }
    },

    /**
     * Refresh a table list without page reload
     * @param {string} containerId - The ID of the container element (e.g., 'members-list')
     * @param {Function} fetchFn - Async function that returns array of items
     * @param {Function} renderFn - Function that takes an item and returns HTML string
     * @param {string} emptyMessage - Message to show when list is empty
     */
    async refreshTableList(containerId, fetchFn, renderFn, emptyMessage = 'No items found.') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Container #${containerId} not found`);
            return;
        }

        try {
            this.showLoading(container, 'table');
            const items = await fetchFn();

            if (items && items.length > 0) {
                container.innerHTML = items.map(renderFn).join('');
            } else {
                this.showEmpty(container, emptyMessage, 'table');
            }
        } catch (err) {
            console.error('Error refreshing list:', err);
            this.showContainerError(container, 'Error loading data', 'table');
        }
    },

    /**
     * Refresh a card/grid list without page reload
     * @param {string} containerId - The ID of the container element
     * @param {Function} fetchFn - Async function that returns array of items
     * @param {Function} renderFn - Function that takes an item and returns HTML string
     * @param {string} emptyMessage - Message to show when list is empty
     */
    async refreshCardList(containerId, fetchFn, renderFn, emptyMessage = 'No items found.') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Container #${containerId} not found`);
            return;
        }

        try {
            this.showLoading(container, 'card');
            const items = await fetchFn();

            if (items && items.length > 0) {
                container.innerHTML = items.map(renderFn).join('');
            } else {
                this.showEmpty(container, emptyMessage, 'card');
            }
        } catch (err) {
            console.error('Error refreshing list:', err);
            this.showContainerError(container, 'Error loading data', 'card');
        }
    },

    // ========================================
    // FORM HANDLING
    // ========================================

    /**
     * Generic form submission handler
     * @param {HTMLFormElement} form - The form element
     * @param {Function} submitFn - Async function that handles form data, returns true on success
     * @param {Function} refreshFn - Optional async function to refresh data after success
     * @returns {boolean} Success status
     */
    async handleFormSubmit(form, submitFn, refreshFn) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        const result = await submitFn(data);
        if (result) {
            form.reset();
            // Close modal if present
            const modal = form.closest('.modal');
            if (modal) {
                const bootstrapModal = bootstrap.Modal.getInstance(modal);
                if (bootstrapModal) bootstrapModal.hide();
            }
            // Refresh the list
            if (refreshFn) await refreshFn();
        }
        return result;
    },

    /**
     * Get form data as object
     * @param {HTMLFormElement} form - The form element
     * @returns {Object} Form data as key-value pairs
     */
    getFormData(form) {
        const formData = new FormData(form);
        return Object.fromEntries(formData.entries());
    },

    /**
     * Populate a form with data
     * @param {HTMLFormElement} form - The form element
     * @param {Object} data - Data to populate
     */
    populateForm(form, data) {
        if (!form || !data) return;

        Object.keys(data).forEach(key => {
            const field = form.elements[key];
            if (field) {
                if (field.type === 'checkbox') {
                    field.checked = Boolean(data[key]);
                } else if (field.type === 'radio') {
                    const radio = form.querySelector(`input[name="${key}"][value="${data[key]}"]`);
                    if (radio) radio.checked = true;
                } else {
                    field.value = data[key] ?? '';
                }
            }
        });
    },

    // ========================================
    // URL & NAVIGATION HELPERS
    // ========================================

    /**
     * Get URL parameter value
     * @param {string} param - Parameter name
     * @returns {string|null} Parameter value or null
     */
    getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    },

    /**
     * Set URL parameter without page reload
     * @param {string} param - Parameter name
     * @param {string} value - Parameter value
     */
    setUrlParam(param, value) {
        const url = new URL(window.location);
        if (value) {
            url.searchParams.set(param, value);
        } else {
            url.searchParams.delete(param);
        }
        window.history.pushState({}, '', url);
    },

    // ========================================
    // MODAL HELPERS
    // ========================================

    /**
     * Show a Bootstrap modal
     * @param {string} modalId - Modal element ID
     */
    showModal(modalId) {
        const modalEl = document.getElementById(modalId);
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    },

    /**
     * Hide a Bootstrap modal
     * @param {string} modalId - Modal element ID
     */
    hideModal(modalId) {
        const modalEl = document.getElementById(modalId);
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
    },

    // ========================================
    // TEXT UTILITIES
    // ========================================

    /**
     * Truncate text with ellipsis
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    truncate(text, maxLength = 50) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    },

    /**
     * Capitalize first letter
     * @param {string} str - String to capitalize
     * @returns {string} Capitalized string
     */
    capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    /**
     * Convert snake_case or kebab-case to Title Case
     * @param {string} str - String to convert
     * @returns {string} Title case string
     */
    toTitleCase(str) {
        if (!str) return '';
        return str.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    // ========================================
    // ROLE-AWARE UI HELPERS
    // ========================================

    /**
     * Show or hide elements based on user role
     * @param {string} selector - CSS selector for elements to control
     * @param {string} minRole - Minimum role required: 'viewer', 'member', 'admin', 'owner'
     * @param {string} orgId - Organization ID (uses current org if not provided)
     */
    async applyRoleVisibility(selector, minRole, orgId) {
        const elements = document.querySelectorAll(selector);
        if (!elements.length) return;

        const hasRole = await window.API?.roles?.hasMinRole(minRole, orgId);
        elements.forEach(el => {
            el.style.display = hasRole ? '' : 'none';
        });
    },

    /**
     * Show elements only for admin or owner roles
     * @param {string} selector - CSS selector for admin-only elements
     * @param {string} orgId - Organization ID (uses current org if not provided)
     */
    async showForAdmin(selector, orgId) {
        return this.applyRoleVisibility(selector, 'admin', orgId);
    },

    /**
     * Show elements only for owner role
     * @param {string} selector - CSS selector for owner-only elements
     * @param {string} orgId - Organization ID (uses current org if not provided)
     */
    async showForOwner(selector, orgId) {
        return this.applyRoleVisibility(selector, 'owner', orgId);
    },

    /**
     * Disable form fields based on role
     * @param {HTMLFormElement} form - Form element
     * @param {string} minRole - Minimum role required to edit
     * @param {string} orgId - Organization ID (uses current org if not provided)
     */
    async applyRoleFieldAccess(form, minRole, orgId) {
        if (!form) return;

        const hasRole = await window.API?.roles?.hasMinRole(minRole, orgId);
        const fields = form.querySelectorAll('input, select, textarea, button[type="submit"]');

        fields.forEach(field => {
            if (!hasRole) {
                field.disabled = true;
                field.classList.add('cursor-not-allowed', 'opacity-60');
            }
        });
    },

    /**
     * Handle 403 Forbidden errors with user-friendly message
     * @param {Error} err - Error object
     * @param {string} action - Description of what was attempted
     */
    handle403(err, action = 'perform this action') {
        if (err.status === 403) {
            this.showError(`You don't have permission to ${action}`);
            return true;
        }
        return false;
    },

    /**
     * Initialize role-based UI on page load
     * Call this after page renders to apply visibility rules
     */
    async initRoleBasedUI() {
        // Hide admin-only elements if not admin
        await this.showForAdmin('[data-require-role="admin"]');
        await this.showForOwner('[data-require-role="owner"]');

        // Apply to common patterns
        await this.showForAdmin('.admin-only');
        await this.showForOwner('.owner-only');
    },

    // ========================================
    // EDITION-AWARE UI HELPERS
    // ========================================

    /**
     * Cache for organization edition features
     * @private
     */
    _editionFeaturesCache: {},
    _editionCacheTime: {},
    _EDITION_CACHE_TTL: 60000, // 1 minute

    /**
     * Get finance features for an organization
     * @param {string} orgId - Organization ID
     * @returns {Promise<Object>} Finance features object
     */
    async getEditionFeatures(orgId) {
        if (!orgId) return null;

        const now = Date.now();
        const cached = this._editionFeaturesCache[orgId];
        const cacheTime = this._editionCacheTime[orgId] || 0;

        // Return cached if valid
        if (cached && (now - cacheTime) < this._EDITION_CACHE_TTL) {
            return cached;
        }

        try {
            const token = window.App?.pb?.authStore?.token || localStorage.getItem('orgmeet_token');
            if (!token) return null;

            const response = await fetch(`/api/v1/admin/org-settings/effective?organization_id=${orgId}&scope=finance`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                // Fallback heuristic: infer features by probing accessible endpoints
                const inferred = await this._inferFinanceFeatures(orgId, token);
                return inferred;
            }

            const data = await response.json();
            const financeConfig = data.settings?.finance || {};
            const resolvedEdition = financeConfig.edition || 'startup';
            const editionDefaults = resolvedEdition === 'nonprofit' ? {
                accounting_basis: 'nonprofit_gaap',
                enable_rev_rec: true,
                enable_contracts: true,
                enable_restrictions: true,
                enable_donations: true,
                enable_budgeting: true
            } : {
                accounting_basis: 'cash',
                enable_rev_rec: false,
                enable_contracts: false,
                enable_restrictions: false,
                enable_donations: false,
                enable_budgeting: false
            };

            const features = {
                edition: resolvedEdition,
                accounting_basis: financeConfig.accounting_basis || editionDefaults.accounting_basis,
                enable_rev_rec: (financeConfig.enable_rev_rec ?? editionDefaults.enable_rev_rec),
                enable_contracts: (financeConfig.enable_contracts ?? editionDefaults.enable_contracts),
                enable_restrictions: (financeConfig.enable_restrictions ?? editionDefaults.enable_restrictions),
                enable_donations: (financeConfig.enable_donations ?? editionDefaults.enable_donations),
                enable_budgeting: (financeConfig.enable_budgeting ?? editionDefaults.enable_budgeting)
            };

            // Safety override: never enable advanced features for startup edition
            if (features.edition === 'startup') {
                features.enable_rev_rec = false;
                features.enable_contracts = false;
            }

            // Cache the result
            this._editionFeaturesCache[orgId] = features;
            this._editionCacheTime[orgId] = now;

            return features;
        } catch (err) {
            console.warn('Error fetching edition features:', err);
            return this._getDefaultFeatures();
        }
    },

    /**
     * Infer finance features by probing accessible endpoints when admin settings are unavailable
     * @private
     */
    async _inferFinanceFeatures(orgId, token) {
        const defaults = this._getDefaultFeatures();
        try {
            const headers = { 'Authorization': `Bearer ${token}` };
            // Probe contracts
            const contractsResp = await fetch(`/api/v1/finance/contracts?organization_id=${orgId}&limit=1`, { headers });
            const contractsEnabled = contractsResp && contractsResp.ok;

            // Probe rev rec schedules
            const schedResp = await fetch(`/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}&limit=1`, { headers });
            const revRecEnabled = schedResp && schedResp.ok;

            const features = {
                ...defaults,
                enable_contracts: !!contractsEnabled,
                enable_rev_rec: !!revRecEnabled,
                edition: (contractsEnabled || revRecEnabled) ? 'nonprofit' : 'startup'
            };

            // Cache inferred result
            const now = Date.now();
            this._editionFeaturesCache[orgId] = features;
            this._editionCacheTime[orgId] = now;
            return features;
        } catch (err) {
            console.warn('Failed to infer finance features:', err);
            return defaults;
        }
    },

    /**
     * Get default features (Startup edition)
     * @private
     */
    _getDefaultFeatures() {
        return {
            edition: 'startup',
            accounting_basis: 'cash',
            enable_rev_rec: false,
            enable_contracts: false,
            enable_restrictions: false,
            enable_donations: false,
            enable_budgeting: false
        };
    },

    /**
     * Clear edition features cache (call after settings change)
     * @param {string} orgId - Organization ID (optional, clears all if not provided)
     */
    clearEditionCache(orgId) {
        if (orgId) {
            delete this._editionFeaturesCache[orgId];
            delete this._editionCacheTime[orgId];
        } else {
            this._editionFeaturesCache = {};
            this._editionCacheTime = {};
        }
    },

    /**
     * Show or hide elements based on edition feature flags
     * @param {string} selector - CSS selector for elements to control
     * @param {string} featureFlag - Feature flag name: 'enable_rev_rec', 'enable_contracts', etc.
     * @param {string} orgId - Organization ID
     */
    async applyEditionVisibility(selector, featureFlag, orgId) {
        const elements = document.querySelectorAll(selector);
        if (!elements.length) return;

        const features = await this.getEditionFeatures(orgId);
        if (!features) {
            // Hide by default if we can't get features
            elements.forEach(el => el.style.display = 'none');
            return;
        }

        const isEnabled = features[featureFlag] || false;
        elements.forEach(el => {
            el.style.display = isEnabled ? '' : 'none';
        });
    },

    /**
     * Show or hide elements based on edition type
     * @param {string} selector - CSS selector for elements to control
     * @param {string|string[]} editions - Edition(s) to show for: 'startup', 'nonprofit', or array of both
     * @param {string} orgId - Organization ID
     */
    async applyEditionTypeVisibility(selector, editions, orgId) {
        const elements = document.querySelectorAll(selector);
        if (!elements.length) return;

        const features = await this.getEditionFeatures(orgId);
        if (!features) {
            elements.forEach(el => el.style.display = 'none');
            return;
        }

        const editionList = Array.isArray(editions) ? editions : [editions];
        const shouldShow = editionList.includes(features.edition);

        elements.forEach(el => {
            el.style.display = shouldShow ? '' : 'none';
        });
    },

    /**
     * Show elements only for Nonprofit edition
     * @param {string} selector - CSS selector for nonprofit-only elements
     * @param {string} orgId - Organization ID
     */
    async showForNonprofit(selector, orgId) {
        return this.applyEditionTypeVisibility(selector, 'nonprofit', orgId);
    },

    /**
     * Show elements only for Startup edition
     * @param {string} selector - CSS selector for startup-only elements
     * @param {string} orgId - Organization ID
     */
    async showForStartup(selector, orgId) {
        return this.applyEditionTypeVisibility(selector, 'startup', orgId);
    },

    /**
     * Initialize edition-based UI visibility
     * Call this after page renders to apply edition-based visibility rules
     * @param {string} orgId - Organization ID
     */
    async initEditionBasedUI(orgId) {
        if (!orgId) return;

        // Apply data attribute-based visibility
        // Elements with data-edition-feature="enable_rev_rec" will be shown/hidden based on that flag
        const featureElements = document.querySelectorAll('[data-edition-feature]');
        for (const el of featureElements) {
            const feature = el.getAttribute('data-edition-feature');
            const features = await this.getEditionFeatures(orgId);
            if (features) {
                el.style.display = features[feature] ? '' : 'none';
            }
        }

        // Apply edition type visibility
        // Elements with data-edition="nonprofit" will only show for nonprofit edition
        const editionElements = document.querySelectorAll('[data-edition]');
        for (const el of editionElements) {
            const edition = el.getAttribute('data-edition');
            const features = await this.getEditionFeatures(orgId);
            if (features) {
                const editions = edition.split(',').map(e => e.trim());
                el.style.display = editions.includes(features.edition) ? '' : 'none';
            }
        }

        // Apply common patterns
        await this.applyEditionVisibility('.rev-rec-only', 'enable_rev_rec', orgId);
        await this.applyEditionVisibility('.contracts-only', 'enable_contracts', orgId);
        await this.applyEditionVisibility('.donations-only', 'enable_donations', orgId);
        await this.applyEditionVisibility('.restrictions-only', 'enable_restrictions', orgId);
        await this.applyEditionVisibility('.budgeting-only', 'enable_budgeting', orgId);
        await this.showForNonprofit('.nonprofit-only', orgId);
        await this.showForStartup('.startup-only', orgId);
    }
};

// Export for use
window.UI = UI;
