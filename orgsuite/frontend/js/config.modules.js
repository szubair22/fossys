/**
 * OrgSuite Module Configuration
 *
 * This file controls which modules are enabled in the application.
 * Modules can be enabled/disabled based on deployment stage or licensing.
 *
 * Deployment Stages:
 * - Stage 1: Governance (OrgMeet) - Meetings, agendas, minutes, motions, basic members, documents
 * - Stage 2: Collaboration - Chat, real-time collaboration
 * - Stage 3: Membership - Enhanced member directory and management
 * - Stage 4: Dashboard Metrics - Analytics and reporting
 * - Stage 5: Finance - Contracts, revenue recognition, donations
 */

(function() {
    'use strict';

    // Current deployment stage (1-5)
    const DEPLOYMENT_STAGE = 1;

    // Module configuration based on deployment stage
    const modulesByStage = {
        1: {
            dashboard: true,
            governance: true,
            documents: true,
            membership: true,
            collaboration: false,
            dashboardMetrics: false,
            finance: false,
            admin: true,
            crm: false
        },
        2: {
            dashboard: true,
            governance: true,
            documents: true,
            membership: true,
            collaboration: true,
            dashboardMetrics: false,
            finance: false,
            admin: true,
            crm: false
        },
        3: {
            dashboard: true,
            governance: true,
            documents: true,
            membership: true,
            collaboration: true,
            dashboardMetrics: false,
            finance: false,
            admin: true,
            crm: false
        },
        4: {
            dashboard: true,
            governance: true,
            documents: true,
            membership: true,
            collaboration: true,
            dashboardMetrics: true,
            finance: false,
            admin: true,
            crm: true
        },
        5: {
            dashboard: true,
            governance: true,
            documents: true,
            membership: true,
            collaboration: true,
            dashboardMetrics: true,
            finance: true,
            admin: true,
            crm: true
        }
    };

    // Get modules for current stage
    const currentModules = modulesByStage[DEPLOYMENT_STAGE] || modulesByStage[1];

    // Export to window
    window.DEPLOYMENT_STAGE = DEPLOYMENT_STAGE;
    window.OrgSuiteModules = Object.freeze(currentModules);

    // Debug logging in development
    if (window.APP_CONFIG && window.APP_CONFIG.DEBUG) {
        console.log('[OrgSuite] Deployment Stage:', DEPLOYMENT_STAGE);
        console.log('[OrgSuite] Enabled Modules:', currentModules);
    }
})();
