// OrgMeet Frontend Configuration
// This file provides environment-aware configuration for the frontend

(function() {
    'use strict';

    // Default configuration
    // PB_URL should be '/' (site root) so PocketBase SDK makes absolute paths
    // nginx proxies /api/* to pocketbase:8090/api/*
    // SDK internally prepends '/api' to all collection paths
    const defaultConfig = {
        PB_URL: '/',
        JITSI_DOMAIN: 'meet.jit.si',
        SITE_URL: window.location.origin,
        APP_ENV: 'development',
        DEBUG: false
    };

    // Environment detection based on hostname
    function detectEnvironment() {
        const hostname = window.location.hostname;

        // Development environments
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local')) {
            return 'development';
        }

        // Production (everything else)
        return 'production';
    }

    // Build configuration object
    function buildConfig() {
        const env = detectEnvironment();

        // Start with defaults
        const config = { ...defaultConfig };

        // Set environment
        config.APP_ENV = env;
        config.DEBUG = env === 'development';

        // Override with any server-injected config (for SSR scenarios)
        if (window.__ORGMEET_CONFIG__) {
            Object.assign(config, window.__ORGMEET_CONFIG__);
        }

        return Object.freeze(config);
    }

    // Export to window
    window.APP_CONFIG = buildConfig();

    // Debug logging in development
    if (window.APP_CONFIG.DEBUG) {
        console.log('[OrgMeet] Configuration loaded:', window.APP_CONFIG);
    }
})();
