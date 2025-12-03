/**
 * OrgSuite Layout System
 *
 * Provides:
 * - Shared header with Applications menu
 * - Theme toggle (light/dark mode)
 * - Module navigation
 * - Organization switcher
 * - Edition badge
 */

const Layout = {
    // Current state
    currentModule: null,
    currentOrgId: null,
    currentEdition: 'startup',

    // Module definitions with pages and setup links
    modules: {
        dashboard: {
            id: 'dashboard',
            name: 'Dashboard',
            icon: '<path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>',
            description: 'Overview and quick actions',
            pages: [
                { name: 'Dashboard', url: '/pages/dashboard.html', icon: '<path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>' }
            ],
            setup: []
        },
        governance: {
            id: 'governance',
            name: 'Governance',
            icon: '<path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V9h14v10zm0-12H5V5h14v2z"/>',
            description: 'Meetings, committees, and decisions',
            pages: [
                { name: 'Meetings', url: '/pages/meetings.html', icon: '<path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>' },
                { name: 'Projects', url: '/pages/projects.html', icon: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>' }
            ],
            setup: [
                { name: 'Governance Settings', url: '/pages/admin_governance.html', icon: '<path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>' }
            ]
        },
        membership: {
            id: 'membership',
            name: 'Membership',
            icon: '<path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>',
            description: 'Members, contacts, and relationships',
            pages: [
                { name: 'Members', url: '/pages/members.html', icon: '<path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3z"/>' },
                { name: 'Contacts', url: '/pages/contacts.html', icon: '<path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-1 14H5c-.55 0-1-.45-1-1v-5h16v5c0 .55-.45 1-1 1z"/>' }
            ],
            setup: [
                { name: 'Membership Settings', url: '/pages/admin_membership.html', icon: '<path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>' }
            ]
        },
        finance: {
            id: 'finance',
            name: 'Finance',
            icon: '<path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>',
            description: 'Accounting, donations, and revenue',
            pages: [
                { name: 'Chart of Accounts', url: '/pages/finance_accounts.html', icon: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>' },
                { name: 'Journal Entries', url: '/pages/finance_journal.html', icon: '<path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>' },
                { name: 'Donations', url: '/pages/finance_donations.html', icon: '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>', editionFeature: 'enable_donations' },
                { name: 'Contracts', url: '/pages/finance_contracts.html', icon: '<path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/>', editionFeature: 'enable_contracts' },
                { name: 'Revenue Recognition', url: '/pages/finance_rev_rec.html', icon: '<path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>', editionFeature: 'enable_rev_rec' }
            ],
            setup: [
                { name: 'Finance Settings', url: '/pages/admin_finance.html', icon: '<path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>' }
            ]
        },
        documents: {
            id: 'documents',
            name: 'Documents',
            icon: '<path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>',
            description: 'File storage and management',
            pages: [
                { name: 'Documents', url: '/pages/documents.html', icon: '<path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>' }
            ],
            setup: []
        },
        admin: {
            id: 'admin',
            name: 'Administration',
            icon: '<path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>',
            description: 'System configuration and settings',
            pages: [
                { name: 'Organization Settings', url: '/pages/admin_org_settings.html', icon: '<path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10z"/>' },
                { name: 'Governance Settings', url: '/pages/admin_governance.html', icon: '<path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>' },
                { name: 'Membership Settings', url: '/pages/admin_membership.html', icon: '<path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3z"/>' },
                { name: 'Finance Settings', url: '/pages/admin_finance.html', icon: '<path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85z"/>' }
            ],
            setup: [
                { name: 'App Settings', url: '/pages/admin_app_settings.html', icon: '<path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>', superadminOnly: true }
            ]
        }
    },

    // ========================================
    // INITIALIZATION
    // ========================================

    /**
     * Initialize the layout system
     * @param {Object} options - Configuration options
     * @param {string} options.module - Current module ID
     * @param {string} options.page - Current page ID
     */
    init(options = {}) {
        this.currentModule = options.module || this.detectCurrentModule();
        this.initTheme();
        this.renderHeader();
        this.renderAppsOverlay();
        this.setupEventListeners();

        // Load organization and edition info
        this.loadOrgInfo();
    },

    /**
     * Detect current module from URL
     */
    detectCurrentModule() {
        const path = window.location.pathname;

        if (path.includes('dashboard')) return 'dashboard';
        if (path.includes('meeting') || path.includes('project')) return 'governance';
        if (path.includes('member') || path.includes('contact')) return 'membership';
        if (path.includes('finance') && !path.includes('admin')) return 'finance';
        if (path.includes('document')) return 'documents';
        if (path.includes('admin')) return 'admin';

        return 'dashboard';
    },

    // ========================================
    // THEME MANAGEMENT
    // ========================================

    /**
     * Initialize theme from localStorage
     */
    initTheme() {
        const savedTheme = localStorage.getItem('orgmeet_theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    },

    /**
     * Toggle between light and dark mode
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('orgmeet_theme', newTheme);

        // Update toggle icon
        this.updateThemeIcon();
    },

    /**
     * Update theme toggle icon
     */
    updateThemeIcon() {
        const toggle = document.getElementById('theme-toggle');
        if (!toggle) return;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        toggle.innerHTML = isDark
            ? '<svg viewBox="0 0 24 24"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>'
            : '<svg viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>';
    },

    // ========================================
    // HEADER RENDERING
    // ========================================

    /**
     * Render the application header
     */
    renderHeader() {
        const header = document.querySelector('.app-header');
        if (!header) return;

        // Check login status via localStorage (more reliable at init time) and API if available
        const token = localStorage.getItem('orgmeet_token');
        const isLoggedIn = !!token || (window.API && window.API.auth && window.API.auth.isLoggedIn && window.API.auth.isLoggedIn());
        const user = window.App?.getUser?.() || JSON.parse(localStorage.getItem('orgmeet_user') || '{}');
        const displayName = user.display_name || user.name || user.email || 'User';
        const initial = displayName.charAt(0).toUpperCase();

        header.innerHTML = `
            <div class="app-header-inner">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <a href="/" class="app-logo">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                        <span>OrgSuite</span>
                    </a>
                    ${isLoggedIn ? `
                        <button class="apps-btn" onclick="Layout.toggleAppsMenu()" data-testid="apps-menu-btn">
                            <svg viewBox="0 0 24 24"><path d="M4 8h4V4H4v4zm6 12h4v-4h-4v4zm-6 0h4v-4H4v4zm0-6h4v-4H4v4zm6 0h4v-4h-4v4zm6-10v4h4V4h-4zm-6 4h4V4h-4v4zm6 6h4v-4h-4v4zm0 6h4v-4h-4v4z"/></svg>
                            <span>Applications</span>
                        </button>
                    ` : ''}
                </div>
                <div class="header-actions">
                    ${isLoggedIn ? `
                        <select id="header-org-selector" class="form-select" style="width: 200px; padding: 0.375rem 0.75rem; font-size: 0.875rem;" onchange="Layout.onOrgChange(this.value)">
                            <option value="">Loading...</option>
                        </select>
                        <span id="edition-badge" class="edition-badge" data-testid="edition-badge">Startup</span>
                    ` : ''}
                    <button id="theme-toggle" class="theme-toggle" onclick="Layout.toggleTheme()" title="Toggle theme">
                        <svg viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>
                    </button>
                    ${isLoggedIn ? `
                        <div class="relative" id="user-menu-container">
                            <button class="user-menu-btn" onclick="Layout.toggleUserMenu()">
                                <div class="user-avatar">${initial}</div>
                                <span style="font-size: 0.875rem;">${displayName}</span>
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style="opacity: 0.5;"><path d="M7 10l5 5 5-5z"/></svg>
                            </button>
                            <div id="user-dropdown" class="hidden" style="position: absolute; right: 0; top: 100%; margin-top: 0.5rem; width: 12rem; background: var(--color-bg-elevated); border: 1px solid var(--color-border-primary); border-radius: var(--radius-md); box-shadow: var(--shadow-lg); z-index: 50; overflow: hidden;">
                                <a href="/pages/account.html" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; color: var(--color-text-primary); text-decoration: none; font-size: 0.875rem; transition: background var(--transition-fast);" onmouseover="this.style.background='var(--color-bg-hover)'" onmouseout="this.style.background='transparent'">
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="opacity: 0.5;"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                                    My Account
                                </a>
                                <hr style="margin: 0; border: none; border-top: 1px solid var(--color-border-secondary);">
                                <button onclick="App.logout()" style="display: flex; align-items: center; gap: 0.5rem; width: 100%; padding: 0.75rem 1rem; color: var(--color-danger); background: none; border: none; font-size: 0.875rem; cursor: pointer; text-align: left; transition: background var(--transition-fast);" onmouseover="this.style.background='var(--color-danger-bg)'" onmouseout="this.style.background='transparent'">
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/></svg>
                                    Sign Out
                                </button>
                            </div>
                        </div>
                    ` : `
                        <a href="/pages/login.html" style="color: var(--color-text-secondary); text-decoration: none; font-size: 0.875rem; font-weight: 500;">Login</a>
                        <a href="/pages/register.html" class="btn btn-primary">Get Started</a>
                    `}
                </div>
            </div>
        `;

        this.updateThemeIcon();

        if (isLoggedIn) {
            this.loadOrganizations();
        }
    },

    // ========================================
    // APPLICATIONS MENU
    // ========================================

    /**
     * Check if a module is enabled based on OrgSuiteModules config
     * Returns true if:
     * - OrgSuiteModules is not defined (backward compatible)
     * - The module key doesn't exist (backward compatible)
     * - The module flag is not explicitly false
     */
    isModuleEnabled(moduleId) {
        // If OrgSuiteModules is not defined, all modules are enabled
        if (!window.OrgSuiteModules) return true;
        // If key doesn't exist, treat as enabled (backward compatible)
        if (!(moduleId in window.OrgSuiteModules)) return true;
        // Only hide if explicitly set to false
        return window.OrgSuiteModules[moduleId] !== false;
    },

    /**
     * Get list of enabled modules
     */
    getEnabledModules() {
        return Object.values(this.modules).filter(m => this.isModuleEnabled(m.id));
    },

    /**
     * Render the Applications overlay
     */
    renderAppsOverlay() {
        // Check if overlay already exists
        if (document.getElementById('apps-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'apps-overlay';
        overlay.className = 'apps-overlay';
        overlay.setAttribute('data-testid', 'apps-overlay');
        overlay.onclick = (e) => {
            if (e.target === overlay) this.closeAppsMenu();
        };

        // Filter modules based on OrgSuiteModules config
        const enabledModules = this.getEnabledModules();

        const modulesList = enabledModules.map(m => `
            <div class="apps-module-item${m.id === this.currentModule ? ' active' : ''}"
                 data-module="${m.id}"
                 onclick="Layout.selectModule('${m.id}')">
                <svg viewBox="0 0 24 24">${m.icon}</svg>
                <span>${m.name}</span>
            </div>
        `).join('');

        overlay.innerHTML = `
            <div class="apps-panel" onclick="event.stopPropagation()">
                <div class="apps-modules" data-testid="apps-modules">
                    ${modulesList}
                </div>
                <div class="apps-detail" id="apps-detail" data-testid="apps-detail">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.renderModuleDetail(this.currentModule);
    },

    /**
     * Render module detail panel
     */
    renderModuleDetail(moduleId) {
        const module = this.modules[moduleId];
        if (!module) return;

        const detailContainer = document.getElementById('apps-detail');
        if (!detailContainer) return;

        // Filter pages based on edition features
        const visiblePages = module.pages.filter(page => {
            if (!page.editionFeature) return true;
            return this.isFeatureEnabled(page.editionFeature);
        });

        const pagesHtml = visiblePages.map(page => `
            <a href="${page.url}" class="apps-link" onclick="Layout.closeAppsMenu()">
                <svg viewBox="0 0 24 24">${page.icon}</svg>
                <span>${page.name}</span>
            </a>
        `).join('');

        const setupHtml = module.setup.length > 0 ? `
            <div class="apps-links-section">
                <div class="apps-links-title">Setup</div>
                <div class="apps-links-grid">
                    ${module.setup.map(item => `
                        <a href="${item.url}" class="apps-link" onclick="Layout.closeAppsMenu()">
                            <svg viewBox="0 0 24 24">${item.icon}</svg>
                            <span>${item.name}</span>
                        </a>
                    `).join('')}
                </div>
            </div>
        ` : '';

        detailContainer.innerHTML = `
            <div class="apps-detail-header">
                <h3 class="apps-detail-title">${module.name}</h3>
                <p class="apps-detail-desc">${module.description}</p>
            </div>
            <div class="apps-links-section">
                <div class="apps-links-title">Pages</div>
                <div class="apps-links-grid">
                    ${pagesHtml}
                </div>
            </div>
            ${setupHtml}
        `;
    },

    /**
     * Select a module in the apps menu
     */
    selectModule(moduleId) {
        // Update active state
        document.querySelectorAll('.apps-module-item').forEach(el => {
            el.classList.toggle('active', el.dataset.module === moduleId);
        });

        this.renderModuleDetail(moduleId);
    },

    /**
     * Toggle apps menu visibility
     */
    toggleAppsMenu() {
        const overlay = document.getElementById('apps-overlay');
        if (overlay) {
            overlay.classList.toggle('active');

            if (overlay.classList.contains('active')) {
                // Focus trap
                document.addEventListener('keydown', this.handleAppsKeydown);
            } else {
                document.removeEventListener('keydown', this.handleAppsKeydown);
            }
        }
    },

    /**
     * Close apps menu
     */
    closeAppsMenu() {
        const overlay = document.getElementById('apps-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            document.removeEventListener('keydown', this.handleAppsKeydown);
        }
    },

    /**
     * Handle keyboard events in apps menu
     */
    handleAppsKeydown(e) {
        if (e.key === 'Escape') {
            Layout.closeAppsMenu();
        }
    },

    // ========================================
    // USER MENU
    // ========================================

    toggleUserMenu() {
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('hidden');

            if (!dropdown.classList.contains('hidden')) {
                const closeDropdown = (e) => {
                    const container = document.getElementById('user-menu-container');
                    if (container && !container.contains(e.target)) {
                        dropdown.classList.add('hidden');
                        document.removeEventListener('click', closeDropdown);
                    }
                };
                setTimeout(() => document.addEventListener('click', closeDropdown), 10);
            }
        }
    },

    // ========================================
    // ORGANIZATION & EDITION
    // ========================================

    /**
     * Load organizations into header selector
     */
    async loadOrganizations() {
        const selector = document.getElementById('header-org-selector');
        if (!selector) return;

        try {
            // Prefer App.getOrganizations to avoid API init race; fallback to API
            let orgs = await window.App?.getOrganizations?.();
            if (!orgs || !Array.isArray(orgs)) {
                const resp = await window.API?.organizations?.list?.();
                orgs = resp?.items || resp || [];
            }

            if (orgs.length === 0) {
                selector.innerHTML = '<option value="">No organizations</option>';
                return;
            }

            selector.innerHTML = orgs.map(org =>
                `<option value="${org.id}">${org.name}</option>`
            ).join('');

            // Check URL param first for org selection
            const urlOrgId = window.UI?.getUrlParam?.('org');
            if (urlOrgId && orgs.find(o => o.id === urlOrgId)) {
                selector.value = urlOrgId;
                this.currentOrgId = urlOrgId;
            } else {
                // Fallback to saved org or first
                const savedOrgId = localStorage.getItem('orgmeet_current_org');
                if (savedOrgId && orgs.find(o => o.id === savedOrgId)) {
                    selector.value = savedOrgId;
                    this.currentOrgId = savedOrgId;
                } else {
                    this.currentOrgId = orgs[0].id;
                    selector.value = this.currentOrgId;
                }
            }

            this.updateEditionBadge();
            // Notify pages of initial org selection
            window.dispatchEvent(new CustomEvent('orgchange', { detail: { orgId: this.currentOrgId } }));
        } catch (err) {
            console.error('Failed to load organizations:', err);
            selector.innerHTML = '<option value="">Error loading</option>';
        }
    },

    /**
     * Handle organization change
     */
    onOrgChange(orgId) {
        this.currentOrgId = orgId;
        window.API?.org?.setCurrentId?.(orgId);
        this.updateEditionBadge();

        // Dispatch event for pages to handle
        window.dispatchEvent(new CustomEvent('orgchange', { detail: { orgId } }));
    },

    /**
     * Load organization info
     */
    async loadOrgInfo() {
        if (!this.currentOrgId) return;
        await this.updateEditionBadge();
    },

    /**
     * Update the edition badge
     */
    async updateEditionBadge() {
        const badge = document.getElementById('edition-badge');
        if (!badge || !this.currentOrgId) return;

        try {
            const features = await window.UI?.getEditionFeatures?.(this.currentOrgId);
            if (features) {
                this.currentEdition = features.edition || 'startup';
                badge.textContent = this.currentEdition === 'nonprofit' ? 'Nonprofit' : 'Startup';
                badge.classList.toggle('nonprofit', this.currentEdition === 'nonprofit');

                // Re-render module detail to update visible pages
                this.renderModuleDetail(this.currentModule);
            }
        } catch (err) {
            console.error('Failed to get edition:', err);
        }
    },

    /**
     * Check if a feature is enabled
     */
    isFeatureEnabled(featureName) {
        // This is a simple check - in real app would use cached features
        return this.currentEdition === 'nonprofit';
    },

    // ========================================
    // MODULE NAVIGATION
    // ========================================

    /**
     * Render module-level navigation
     * @param {string} moduleId - Module ID
     * @param {string} currentPage - Current page identifier
     */
    renderModuleNav(moduleId, currentPage) {
        const module = this.modules[moduleId];
        if (!module || !module.pages.length) return '';

        const navContainer = document.querySelector('.module-nav');
        if (!navContainer) return;

        // Filter visible pages
        const visiblePages = module.pages.filter(page => {
            if (!page.editionFeature) return true;
            return this.isFeatureEnabled(page.editionFeature);
        });

        const navItems = visiblePages.map(page => {
            const isActive = currentPage === page.name.toLowerCase().replace(/\s+/g, '-');
            return `
                <a href="${page.url}" class="module-nav-item${isActive ? ' active' : ''}">
                    ${page.name}
                </a>
            `;
        }).join('');

        // Add setup link if module has setup
        const setupLink = module.setup.length > 0 ? `
            <div class="module-nav-divider"></div>
            <a href="${module.setup[0].url}" class="module-nav-item">
                <svg viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/></svg>
                Setup
            </a>
        ` : '';

        navContainer.innerHTML = `
            <div class="module-nav-inner">
                ${navItems}
                ${setupLink}
            </div>
        `;
    },

    // ========================================
    // EVENT LISTENERS
    // ========================================

    setupEventListeners() {
        // Close menus on outside click
        document.addEventListener('click', (e) => {
            // Close user menu
            const userContainer = document.getElementById('user-menu-container');
            const userDropdown = document.getElementById('user-dropdown');
            if (userContainer && userDropdown && !userContainer.contains(e.target)) {
                userDropdown.classList.add('hidden');
            }
        });
    }
};

// Export
window.Layout = Layout;
