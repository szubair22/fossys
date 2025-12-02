/**
 * Dashboard Metrics Module
 *
 * Provides metrics management functionality for the dashboard:
 * - Display metric cards
 * - Add/edit/delete metrics
 * - Update metric values
 * - Setup wizard for new organizations
 * - History view
 */

const DashboardMetrics = {
    // State
    currentOrgId: null,
    metrics: [],
    isAdmin: false,

    // Value type formatters
    formatters: {
        number: (value) => {
            const num = parseFloat(value);
            if (isNaN(num)) return '0';
            return new Intl.NumberFormat('en-US', {
                maximumFractionDigits: 2
            }).format(num);
        },
        currency: (value, currency = 'USD') => {
            const num = parseFloat(value);
            if (isNaN(num)) return '$0.00';
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
            }).format(num);
        },
        percent: (value) => {
            const num = parseFloat(value);
            if (isNaN(num)) return '0%';
            return new Intl.NumberFormat('en-US', {
                style: 'percent',
                minimumFractionDigits: 0,
                maximumFractionDigits: 1
            }).format(num / 100);
        }
    },

    // Frequency labels
    frequencyLabels: {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
        quarterly: 'Quarterly'
    },

    /**
     * Initialize the metrics module
     */
    async init(orgId) {
        this.currentOrgId = orgId;

        // Check user role
        this.isAdmin = await API.roles.isAdmin(orgId);

        // Load metrics
        await this.loadMetrics();
    },

    /**
     * Load metrics from API
     */
    async loadMetrics() {
        if (!this.currentOrgId) return;

        try {
            const response = await API.dashboard.metrics.list(this.currentOrgId);
            this.metrics = response.items || [];
            this.render();
        } catch (error) {
            console.error('Failed to load metrics:', error);
            UI.showError('Failed to load metrics');
        }
    },

    /**
     * Render the metrics section
     */
    render() {
        const container = document.getElementById('metrics-section');
        if (!container) return;

        // Show empty state or metrics grid
        if (this.metrics.length === 0) {
            this.renderEmptyState(container);
        } else {
            this.renderMetricsGrid(container);
        }
    },

    /**
     * Render empty state for new organizations
     */
    renderEmptyState(container) {
        const canSetup = this.isAdmin;

        container.innerHTML = `
            <div class="metrics-empty-state" data-testid="metrics-empty-state">
                <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
                    <div class="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
                        <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor" class="text-indigo-600">
                            <path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>
                        </svg>
                    </div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">Track Your Key Metrics</h3>
                    <p class="text-gray-500 mb-6 max-w-md mx-auto">
                        Add the 3-7 numbers you care about most. Track active members, revenue, donations, events, and more.
                    </p>
                    ${canSetup ? `
                        <button onclick="DashboardMetrics.openSetupWizard()" class="btn btn-primary" data-testid="metrics-setup-btn">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="margin-right: 0.5rem;">
                                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                            </svg>
                            Get Started
                        </button>
                    ` : `
                        <p class="text-sm text-gray-400">Ask an admin to set up metrics for this organization.</p>
                    `}
                </div>
            </div>
        `;
    },

    /**
     * Render the metrics grid
     */
    renderMetricsGrid(container) {
        const addButton = this.isAdmin ? `
            <button onclick="DashboardMetrics.openAddMetricModal()" class="btn btn-primary" data-testid="add-metric-btn">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="margin-right: 0.5rem;">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                </svg>
                Add Metric
            </button>
        ` : '';

        const cards = this.metrics.map(m => this.renderMetricCard(m)).join('');

        container.innerHTML = `
            <div class="metrics-section">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-gray-900">Key Metrics</h2>
                    ${addButton}
                </div>
                <div class="metrics-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="metrics-grid">
                    ${cards}
                </div>
            </div>
        `;
    },

    /**
     * Render a single metric card
     */
    renderMetricCard(metric) {
        const formatter = this.formatters[metric.value_type] || this.formatters.number;
        const latestValue = metric.latest_value;
        const displayValue = latestValue
            ? formatter(latestValue.value, metric.currency)
            : '—';

        // Calculate last updated
        let lastUpdated = 'Never updated';
        if (latestValue) {
            const updateDate = new Date(latestValue.created);
            const now = new Date();
            const diffDays = Math.floor((now - updateDate) / (1000 * 60 * 60 * 24));
            if (diffDays === 0) {
                lastUpdated = 'Updated today';
            } else if (diffDays === 1) {
                lastUpdated = 'Updated yesterday';
            } else if (diffDays < 7) {
                lastUpdated = `Updated ${diffDays} days ago`;
            } else {
                lastUpdated = `Updated ${updateDate.toLocaleDateString()}`;
            }
        }

        // Progress toward target
        let progressHtml = '';
        if (metric.target_value && latestValue) {
            const current = parseFloat(latestValue.value);
            const target = parseFloat(metric.target_value);
            const percent = Math.min(100, Math.round((current / target) * 100));
            progressHtml = `
                <div class="mt-3 pt-3 border-t border-gray-100">
                    <div class="flex justify-between text-xs text-gray-500 mb-1">
                        <span>Target: ${formatter(target, metric.currency)}</span>
                        <span>${percent}%</span>
                    </div>
                    <div class="w-full bg-gray-100 rounded-full h-1.5">
                        <div class="bg-indigo-500 h-1.5 rounded-full transition-all" style="width: ${percent}%"></div>
                    </div>
                </div>
            `;
        }

        // Actions
        const actionsHtml = this.isAdmin ? `
            <div class="flex gap-2 mt-4">
                <button onclick="DashboardMetrics.openUpdateValueModal('${metric.id}')" class="btn btn-sm btn-primary flex-1" data-testid="update-metric-${metric.id}">
                    Update
                </button>
                <button onclick="DashboardMetrics.openHistoryModal('${metric.id}')" class="btn btn-sm btn-secondary" title="View history">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
                    </svg>
                </button>
                <button onclick="DashboardMetrics.openEditMetricModal('${metric.id}')" class="btn btn-sm btn-secondary" title="Edit metric">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                </button>
            </div>
        ` : `
            <div class="flex gap-2 mt-4">
                <button onclick="DashboardMetrics.openHistoryModal('${metric.id}')" class="btn btn-sm btn-secondary flex-1">
                    View History
                </button>
            </div>
        `;

        return `
            <div class="metric-card bg-white rounded-xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow" data-testid="metric-card-${metric.id}">
                <div class="flex justify-between items-start mb-2">
                    <h3 class="font-medium text-gray-900">${this.escapeHtml(metric.name)}</h3>
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                        ${this.frequencyLabels[metric.frequency] || metric.frequency}
                    </span>
                </div>
                <div class="text-2xl font-bold text-gray-900 mb-1" data-testid="metric-value-${metric.id}">
                    ${displayValue}
                </div>
                <p class="text-xs text-gray-500" data-testid="metric-updated-${metric.id}">${lastUpdated}</p>
                ${progressHtml}
                ${actionsHtml}
            </div>
        `;
    },

    /**
     * Open the setup wizard modal
     */
    async openSetupWizard() {
        const templates = [
            { name: 'Active Members', description: 'Total number of active members', value_type: 'number', frequency: 'monthly' },
            { name: 'Monthly Revenue', description: 'Total revenue this month', value_type: 'currency', frequency: 'monthly' },
            { name: 'Monthly Donations', description: 'Donations received this month', value_type: 'currency', frequency: 'monthly' },
            { name: 'Events This Month', description: 'Events or meetings held', value_type: 'number', frequency: 'monthly' },
            { name: 'Volunteer Hours', description: 'Volunteer hours contributed', value_type: 'number', frequency: 'monthly' },
            { name: 'New Members', description: 'New members added this period', value_type: 'number', frequency: 'monthly' },
            { name: 'Retention Rate', description: 'Member retention percentage', value_type: 'percent', frequency: 'quarterly' }
        ];

        const templateCheckboxes = templates.map((t, i) => `
            <label class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                <input type="checkbox" name="template_${i}" value="${i}" class="mt-1" checked>
                <div>
                    <div class="font-medium text-gray-900">${t.name}</div>
                    <div class="text-sm text-gray-500">${t.description}</div>
                </div>
            </label>
        `).join('');

        const modal = document.createElement('div');
        modal.id = 'setup-wizard-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h2 class="modal-title">Set Up Your Metrics</h2>
                    <button onclick="DashboardMetrics.closeModal('setup-wizard-modal')" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="text-gray-600 mb-4">Select the metrics you want to track. You can add more later.</p>
                    <form id="setup-wizard-form">
                        <div class="space-y-2 max-h-96 overflow-y-auto">
                            ${templateCheckboxes}
                        </div>
                        <div class="mt-4 pt-4 border-t">
                            <label class="flex items-start gap-3 p-3 bg-indigo-50 rounded-lg">
                                <input type="checkbox" name="custom" id="add-custom-metric">
                                <div>
                                    <div class="font-medium text-gray-900">Add a custom metric</div>
                                    <input type="text" name="custom_name" placeholder="Metric name" class="form-input mt-2 w-full" style="display: none;" data-testid="custom-metric-name">
                                </div>
                            </label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button onclick="DashboardMetrics.closeModal('setup-wizard-modal')" class="btn btn-secondary">Cancel</button>
                    <button onclick="DashboardMetrics.submitSetupWizard()" class="btn btn-primary" data-testid="wizard-submit-btn">Create Metrics</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Toggle custom metric input
        document.getElementById('add-custom-metric').addEventListener('change', function() {
            const input = document.querySelector('[name="custom_name"]');
            input.style.display = this.checked ? 'block' : 'none';
            if (this.checked) input.focus();
        });
    },

    /**
     * Submit setup wizard
     */
    async submitSetupWizard() {
        const templates = [
            { name: 'Active Members', description: 'Total number of active members', value_type: 'number', frequency: 'monthly' },
            { name: 'Monthly Revenue', description: 'Total revenue this month', value_type: 'currency', frequency: 'monthly' },
            { name: 'Monthly Donations', description: 'Donations received this month', value_type: 'currency', frequency: 'monthly' },
            { name: 'Events This Month', description: 'Events or meetings held', value_type: 'number', frequency: 'monthly' },
            { name: 'Volunteer Hours', description: 'Volunteer hours contributed', value_type: 'number', frequency: 'monthly' },
            { name: 'New Members', description: 'New members added this period', value_type: 'number', frequency: 'monthly' },
            { name: 'Retention Rate', description: 'Member retention percentage', value_type: 'percent', frequency: 'quarterly' }
        ];

        const form = document.getElementById('setup-wizard-form');
        const metricsToCreate = [];

        // Get selected templates
        templates.forEach((t, i) => {
            const checkbox = form.querySelector(`[name="template_${i}"]`);
            if (checkbox && checkbox.checked) {
                metricsToCreate.push({
                    name: t.name,
                    description: t.description,
                    value_type: t.value_type,
                    frequency: t.frequency,
                    currency: 'USD'
                });
            }
        });

        // Add custom metric if specified
        const customCheckbox = form.querySelector('#add-custom-metric');
        const customName = form.querySelector('[name="custom_name"]').value.trim();
        if (customCheckbox.checked && customName) {
            metricsToCreate.push({
                name: customName,
                value_type: 'number',
                frequency: 'monthly',
                currency: 'USD'
            });
        }

        if (metricsToCreate.length === 0) {
            UI.showError('Please select at least one metric');
            return;
        }

        try {
            await API.dashboard.metrics.setup(this.currentOrgId, metricsToCreate);
            this.closeModal('setup-wizard-modal');
            UI.showSuccess(`Created ${metricsToCreate.length} metrics`);
            await this.loadMetrics();
        } catch (error) {
            console.error('Setup failed:', error);
            UI.showError('Failed to create metrics: ' + error.message);
        }
    },

    /**
     * Open add metric modal
     */
    openAddMetricModal() {
        const modal = document.createElement('div');
        modal.id = 'add-metric-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2 class="modal-title">Add Metric</h2>
                    <button onclick="DashboardMetrics.closeModal('add-metric-modal')" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="add-metric-form">
                        <div class="form-group">
                            <label class="form-label">Name *</label>
                            <input type="text" name="name" class="form-input" required data-testid="metric-name-input">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <textarea name="description" class="form-input" rows="2"></textarea>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Value Type</label>
                                <select name="value_type" class="form-select" data-testid="metric-type-select">
                                    <option value="number">Number</option>
                                    <option value="currency">Currency</option>
                                    <option value="percent">Percent</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Frequency</label>
                                <select name="frequency" class="form-select" data-testid="metric-frequency-select">
                                    <option value="daily">Daily</option>
                                    <option value="weekly">Weekly</option>
                                    <option value="monthly" selected>Monthly</option>
                                    <option value="quarterly">Quarterly</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Target Value (optional)</label>
                            <input type="number" name="target_value" class="form-input" step="0.01" min="0">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button onclick="DashboardMetrics.closeModal('add-metric-modal')" class="btn btn-secondary">Cancel</button>
                    <button onclick="DashboardMetrics.submitAddMetric()" class="btn btn-primary" data-testid="metric-save-btn">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.querySelector('[name="name"]').focus();
    },

    /**
     * Submit add metric form
     */
    async submitAddMetric() {
        const form = document.getElementById('add-metric-form');
        const formData = new FormData(form);

        const data = {
            name: formData.get('name'),
            description: formData.get('description') || null,
            value_type: formData.get('value_type'),
            frequency: formData.get('frequency'),
            target_value: formData.get('target_value') ? parseFloat(formData.get('target_value')) : null,
            currency: 'USD'
        };

        if (!data.name.trim()) {
            UI.showError('Name is required');
            return;
        }

        try {
            await API.dashboard.metrics.create(this.currentOrgId, data);
            this.closeModal('add-metric-modal');
            UI.showSuccess('Metric created');
            await this.loadMetrics();
        } catch (error) {
            console.error('Failed to create metric:', error);
            UI.showError('Failed to create metric: ' + error.message);
        }
    },

    /**
     * Open edit metric modal
     */
    openEditMetricModal(metricId) {
        const metric = this.metrics.find(m => m.id === metricId);
        if (!metric) return;

        const modal = document.createElement('div');
        modal.id = 'edit-metric-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2 class="modal-title">Edit Metric</h2>
                    <button onclick="DashboardMetrics.closeModal('edit-metric-modal')" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="edit-metric-form" data-metric-id="${metricId}">
                        <div class="form-group">
                            <label class="form-label">Name *</label>
                            <input type="text" name="name" class="form-input" value="${this.escapeHtml(metric.name)}" required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <textarea name="description" class="form-input" rows="2">${this.escapeHtml(metric.description || '')}</textarea>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="form-group">
                                <label class="form-label">Value Type</label>
                                <select name="value_type" class="form-select">
                                    <option value="number" ${metric.value_type === 'number' ? 'selected' : ''}>Number</option>
                                    <option value="currency" ${metric.value_type === 'currency' ? 'selected' : ''}>Currency</option>
                                    <option value="percent" ${metric.value_type === 'percent' ? 'selected' : ''}>Percent</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Frequency</label>
                                <select name="frequency" class="form-select">
                                    <option value="daily" ${metric.frequency === 'daily' ? 'selected' : ''}>Daily</option>
                                    <option value="weekly" ${metric.frequency === 'weekly' ? 'selected' : ''}>Weekly</option>
                                    <option value="monthly" ${metric.frequency === 'monthly' ? 'selected' : ''}>Monthly</option>
                                    <option value="quarterly" ${metric.frequency === 'quarterly' ? 'selected' : ''}>Quarterly</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Target Value (optional)</label>
                            <input type="number" name="target_value" class="form-input" step="0.01" min="0" value="${metric.target_value || ''}">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button onclick="DashboardMetrics.deleteMetric('${metricId}')" class="btn btn-danger" style="margin-right: auto;">Delete</button>
                    <button onclick="DashboardMetrics.closeModal('edit-metric-modal')" class="btn btn-secondary">Cancel</button>
                    <button onclick="DashboardMetrics.submitEditMetric()" class="btn btn-primary">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    },

    /**
     * Submit edit metric form
     */
    async submitEditMetric() {
        const form = document.getElementById('edit-metric-form');
        const metricId = form.dataset.metricId;
        const formData = new FormData(form);

        const data = {
            name: formData.get('name'),
            description: formData.get('description') || null,
            value_type: formData.get('value_type'),
            frequency: formData.get('frequency'),
            target_value: formData.get('target_value') ? parseFloat(formData.get('target_value')) : null
        };

        if (!data.name.trim()) {
            UI.showError('Name is required');
            return;
        }

        try {
            await API.dashboard.metrics.update(this.currentOrgId, metricId, data);
            this.closeModal('edit-metric-modal');
            UI.showSuccess('Metric updated');
            await this.loadMetrics();
        } catch (error) {
            console.error('Failed to update metric:', error);
            UI.showError('Failed to update metric: ' + error.message);
        }
    },

    /**
     * Delete a metric
     */
    async deleteMetric(metricId) {
        if (!confirm('Delete this metric and all its history? This cannot be undone.')) {
            return;
        }

        try {
            await API.dashboard.metrics.delete(this.currentOrgId, metricId);
            this.closeModal('edit-metric-modal');
            UI.showSuccess('Metric deleted');
            await this.loadMetrics();
        } catch (error) {
            console.error('Failed to delete metric:', error);
            UI.showError('Failed to delete metric: ' + error.message);
        }
    },

    /**
     * Open update value modal
     */
    openUpdateValueModal(metricId) {
        const metric = this.metrics.find(m => m.id === metricId);
        if (!metric) return;

        const today = new Date().toISOString().split('T')[0];

        const modal = document.createElement('div');
        modal.id = 'update-value-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 400px;">
                <div class="modal-header">
                    <h2 class="modal-title">Update ${this.escapeHtml(metric.name)}</h2>
                    <button onclick="DashboardMetrics.closeModal('update-value-modal')" class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="update-value-form" data-metric-id="${metricId}">
                        <div class="form-group">
                            <label class="form-label">Value *</label>
                            <input type="number" name="value" class="form-input" step="0.01" required data-testid="metric-value-input">
                            <p class="text-xs text-gray-500 mt-1">
                                ${metric.value_type === 'percent' ? 'Enter as whole number (e.g., 75 for 75%)' : ''}
                                ${metric.value_type === 'currency' ? 'Enter amount in ' + metric.currency : ''}
                            </p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Effective Date</label>
                            <input type="date" name="effective_date" class="form-input" value="${today}">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Notes (optional)</label>
                            <textarea name="notes" class="form-input" rows="2" placeholder="Any context about this value..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button onclick="DashboardMetrics.closeModal('update-value-modal')" class="btn btn-secondary">Cancel</button>
                    <button onclick="DashboardMetrics.submitUpdateValue()" class="btn btn-primary" data-testid="value-save-btn">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.querySelector('[name="value"]').focus();
    },

    /**
     * Submit update value form
     */
    async submitUpdateValue() {
        const form = document.getElementById('update-value-form');
        const metricId = form.dataset.metricId;
        const formData = new FormData(form);

        const value = formData.get('value');
        if (!value) {
            UI.showError('Value is required');
            return;
        }

        const data = {
            value: parseFloat(value),
            effective_date: formData.get('effective_date') || new Date().toISOString().split('T')[0],
            notes: formData.get('notes') || null
        };

        try {
            await API.dashboard.metrics.addValue(this.currentOrgId, metricId, data);
            this.closeModal('update-value-modal');
            UI.showSuccess('Value updated');
            await this.loadMetrics();
        } catch (error) {
            console.error('Failed to update value:', error);
            UI.showError('Failed to update value: ' + error.message);
        }
    },

    /**
     * Open history modal
     */
    async openHistoryModal(metricId) {
        const metric = this.metrics.find(m => m.id === metricId);
        if (!metric) return;

        // Load full history
        let historyHtml = '<p class="text-gray-500 text-center py-4">Loading...</p>';

        const modal = document.createElement('div');
        modal.id = 'history-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2 class="modal-title">${this.escapeHtml(metric.name)} History</h2>
                    <button onclick="DashboardMetrics.closeModal('history-modal')" class="modal-close">&times;</button>
                </div>
                <div class="modal-body" style="max-height: 400px; overflow-y: auto;" id="history-content">
                    ${historyHtml}
                </div>
                <div class="modal-footer">
                    <button onclick="DashboardMetrics.closeModal('history-modal')" class="btn btn-secondary">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Load history
        try {
            const response = await API.dashboard.metrics.listValues(this.currentOrgId, metricId, 100);
            const values = response.items || [];
            const formatter = this.formatters[metric.value_type] || this.formatters.number;

            if (values.length === 0) {
                historyHtml = '<p class="text-gray-500 text-center py-8">No history yet</p>';
            } else {
                historyHtml = `
                    <table class="w-full">
                        <thead>
                            <tr class="text-left text-xs text-gray-500 border-b">
                                <th class="pb-2">Date</th>
                                <th class="pb-2">Value</th>
                                <th class="pb-2">Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${values.map(v => `
                                <tr class="border-b border-gray-50">
                                    <td class="py-2 text-sm">${new Date(v.effective_date).toLocaleDateString()}</td>
                                    <td class="py-2 font-medium">${formatter(v.value, metric.currency)}</td>
                                    <td class="py-2 text-sm text-gray-500">${this.escapeHtml(v.notes || '—')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }

            document.getElementById('history-content').innerHTML = historyHtml;
        } catch (error) {
            console.error('Failed to load history:', error);
            document.getElementById('history-content').innerHTML =
                '<p class="text-red-500 text-center py-4">Failed to load history</p>';
        }
    },

    /**
     * Close a modal by ID
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            setTimeout(() => modal.remove(), 200);
        }
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

// Export
window.DashboardMetrics = DashboardMetrics;
