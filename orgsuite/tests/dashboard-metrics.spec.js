// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * DASHBOARD METRICS E2E TESTS
 *
 * Tests for the Org Metrics Dashboard feature:
 * - Creating metrics manually
 * - Updating metric values
 * - Viewing metric history
 * - Setup wizard for new organizations
 * - Metrics persistence per organization
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

// Helper to format dates for API calls
const formatDate = (date) => {
  return date.toISOString().split('T')[0];
};

// Helper to login or register a user
async function setupUser(page, prefix = 'test') {
  const email = `${prefix}_${uniqueId()}@example.com`;
  const password = 'TestPass123';

  await page.goto('/pages/register.html');
  await page.waitForLoadState('domcontentloaded');

  await page.fill('#name', `${prefix} User`);
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.fill('#passwordConfirm', password);
  await page.click('button[type="submit"]');

  await page.waitForURL('**/dashboard.html', { timeout: 15000 });
  return { email, password };
}

// Helper to create an organization
async function createOrganization(page, orgName) {
  await page.goto('/pages/organizations.html');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  await page.locator('button:has-text("Create Organization")').first().click();

  const modal = page.locator('#new-org-modal');
  await modal.waitFor({ state: 'visible', timeout: 5000 });

  const orgInput = page.locator('#org-name');
  await orgInput.waitFor({ state: 'visible', timeout: 5000 });
  await orgInput.fill(orgName);

  const responsePromise = page.waitForResponse(resp =>
    resp.url().includes('/api/v1/organizations') && resp.request().method() === 'POST'
  );

  await page.locator('#submit-org-btn').click();

  const response = await responsePromise;
  if (response.status() !== 200 && response.status() !== 201) {
    throw new Error(`Failed to create organization: ${response.status()}`);
  }

  await modal.waitFor({ state: 'hidden', timeout: 5000 });
  await page.waitForTimeout(1000);

  // Get org ID from API
  const orgsResponse = await page.evaluate(async () => {
    const token = window.App?.pb?.authStore?.token || localStorage.getItem('orgmeet_token');
    if (!token) return null;
    const resp = await fetch('/api/v1/organizations', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
  });

  if (orgsResponse && orgsResponse.items && orgsResponse.items.length > 0) {
    const org = orgsResponse.items.find(o => o.name === orgName);
    return org?.id || orgsResponse.items[0].id;
  }
  return null;
}

// Helper to get auth token from page
async function getAuthToken(page) {
  return await page.evaluate(() => {
    return window.App?.pb?.authStore?.token || localStorage.getItem('orgmeet_token');
  });
}


// ============================================================================
// METRIC CREATION TESTS
// ============================================================================

test.describe('Dashboard Metrics: Metric Creation', () => {

  test('can create a manual metric and update its value', async ({ page }) => {
    await setupUser(page, 'metricstest');
    const orgName = `Metrics Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Navigate to dashboard
    await page.goto(`/pages/dashboard.html`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(3000);

    // Select the organization if needed
    const orgSelector = page.locator('[data-testid="org-selector"]');
    if (await orgSelector.isVisible()) {
      await orgSelector.selectOption(orgId);
      await page.waitForTimeout(1500);
    }

    // Check for metrics section - should show empty state
    const metricsSection = page.locator('[data-testid="metrics-section"]');
    await expect(metricsSection).toBeVisible({ timeout: 10000 });

    // Should show empty state for new org
    const emptyState = page.locator('[data-testid="metrics-empty-state"]');
    const setupBtn = page.locator('[data-testid="metrics-setup-btn"]');
    const addMetricBtn = page.locator('[data-testid="add-metric-btn"]');

    // Either empty state or metrics grid should be visible
    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    const hasAddBtn = await addMetricBtn.isVisible().catch(() => false);

    if (hasEmptyState) {
      // Click setup button to create first metric
      await setupBtn.click();
      await page.waitForTimeout(500);

      // Modal should appear
      const setupModal = page.locator('#setup-wizard-modal');
      await expect(setupModal).toBeVisible({ timeout: 5000 });

      // Submit wizard with default selections
      await page.locator('[data-testid="wizard-submit-btn"]').click();

      // Wait for modal to close and metrics to appear
      await setupModal.waitFor({ state: 'hidden', timeout: 10000 });
      await page.waitForTimeout(1000);

      // Metrics should now be visible
      await expect(page.locator('[data-testid="metrics-grid"]')).toBeVisible({ timeout: 10000 });
    } else if (hasAddBtn) {
      // Add metric button visible - click to add metric
      await addMetricBtn.click();
      await page.waitForTimeout(500);

      const modal = page.locator('#add-metric-modal');
      await expect(modal).toBeVisible({ timeout: 5000 });

      // Fill in metric details
      const metricName = `Test Metric ${uniqueId()}`;
      await page.locator('[data-testid="metric-name-input"]').fill(metricName);
      await page.locator('[data-testid="metric-type-select"]').selectOption('number');
      await page.locator('[data-testid="metric-frequency-select"]').selectOption('monthly');

      // Save the metric
      await page.locator('[data-testid="metric-save-btn"]').click();

      // Wait for modal to close
      await modal.waitFor({ state: 'hidden', timeout: 10000 });
      await page.waitForTimeout(1000);

      // Verify metric card appears
      await expect(page.getByText(metricName)).toBeVisible({ timeout: 10000 });
    }

    // Now we should have at least one metric - find an Update button
    const updateBtns = page.locator('button:has-text("Update")');
    const updateBtnCount = await updateBtns.count();

    if (updateBtnCount > 0) {
      // Click first Update button
      await updateBtns.first().click();
      await page.waitForTimeout(500);

      // Value modal should appear
      const valueModal = page.locator('#update-value-modal');
      await expect(valueModal).toBeVisible({ timeout: 5000 });

      // Enter a value
      await page.locator('[data-testid="metric-value-input"]').fill('123');

      // Save the value
      await page.locator('[data-testid="value-save-btn"]').click();

      // Wait for modal to close
      await valueModal.waitFor({ state: 'hidden', timeout: 10000 });
      await page.waitForTimeout(1000);

      // Verify value is shown (could be "123" or formatted)
      await expect(page.getByText('123')).toBeVisible({ timeout: 10000 });
      await expect(page.getByText('Updated today')).toBeVisible({ timeout: 5000 });
    }
  });

  test('can create metric via API', async ({ page }) => {
    await setupUser(page, 'metricapi');
    const orgName = `Metric API Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Create metric via API
    const metricName = `API Metric ${uniqueId()}`;
    const response = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          name: metricName,
          description: 'A test metric created via API',
          value_type: 'number',
          frequency: 'monthly',
          currency: 'USD'
        }
      }
    );

    expect(response.status()).toBe(201);
    const metric = await response.json();
    expect(metric.name).toBe(metricName);
    expect(metric.organization_id).toBe(orgId);
    expect(metric.value_type).toBe('number');
    expect(metric.frequency).toBe('monthly');

    // Add a value via API
    const valueResponse = await page.request.post(
      `/api/v1/dashboard/metrics/${metric.id}/values?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          value: 456.78,
          effective_date: formatDate(new Date()),
          notes: 'Initial value'
        }
      }
    );

    expect(valueResponse.status()).toBe(201);
    const value = await valueResponse.json();
    expect(parseFloat(value.value)).toBe(456.78);

    // Verify metric and value appear in list
    const listResponse = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    expect(listResponse.status()).toBe(200);
    const list = await listResponse.json();
    expect(list.items.length).toBe(1);
    expect(list.items[0].name).toBe(metricName);
    expect(list.items[0].latest_value).toBeTruthy();
    expect(parseFloat(list.items[0].latest_value.value)).toBe(456.78);
  });

});


// ============================================================================
// METRICS PERSISTENCE TESTS
// ============================================================================

test.describe('Dashboard Metrics: Persistence Per Organization', () => {

  test('metrics are scoped to organization', async ({ page }) => {
    await setupUser(page, 'metricscope');

    // Create two organizations
    const org1Name = `Scope Org 1 ${uniqueId()}`;
    const org2Name = `Scope Org 2 ${uniqueId()}`;

    const org1Id = await createOrganization(page, org1Name);
    const org2Id = await createOrganization(page, org2Name);

    const token = await getAuthToken(page);

    // Create metric in org1
    const metric1Response = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: org1Id,
          name: `Org1 Metric ${uniqueId()}`,
          value_type: 'number',
          frequency: 'monthly'
        }
      }
    );
    expect(metric1Response.status()).toBe(201);

    // Create different metric in org2
    const metric2Response = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: org2Id,
          name: `Org2 Metric ${uniqueId()}`,
          value_type: 'currency',
          frequency: 'weekly'
        }
      }
    );
    expect(metric2Response.status()).toBe(201);

    // Verify org1 only has its metric
    const org1Metrics = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${org1Id}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const org1List = await org1Metrics.json();
    expect(org1List.items.length).toBe(1);
    expect(org1List.items[0].value_type).toBe('number');

    // Verify org2 only has its metric
    const org2Metrics = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${org2Id}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const org2List = await org2Metrics.json();
    expect(org2List.items.length).toBe(1);
    expect(org2List.items[0].value_type).toBe('currency');
  });

});


// ============================================================================
// METRIC VALUE HISTORY TESTS
// ============================================================================

test.describe('Dashboard Metrics: History', () => {

  test('metric values history is preserved', async ({ page }) => {
    await setupUser(page, 'metrichistory');
    const orgName = `History Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Create metric
    const metricResponse = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          name: `History Metric ${uniqueId()}`,
          value_type: 'number',
          frequency: 'daily'
        }
      }
    );
    const metric = await metricResponse.json();

    // Add multiple values
    const today = new Date();
    for (let i = 0; i < 5; i++) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);

      await page.request.post(
        `/api/v1/dashboard/metrics/${metric.id}/values?organization_id=${orgId}`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
          data: {
            value: 100 + i * 10,
            effective_date: formatDate(date),
            notes: `Day ${i}`
          }
        }
      );
    }

    // Get values history
    const historyResponse = await page.request.get(
      `/api/v1/dashboard/metrics/${metric.id}/values?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    expect(historyResponse.status()).toBe(200);
    const history = await historyResponse.json();
    expect(history.items.length).toBe(5);
    expect(history.total).toBe(5);

    // Values should be ordered by effective_date desc
    // Most recent first (100), oldest last (140)
    expect(parseFloat(history.items[0].value)).toBe(100);
    expect(parseFloat(history.items[4].value)).toBe(140);
  });

});


// ============================================================================
// SETUP WIZARD TESTS
// ============================================================================

test.describe('Dashboard Metrics: Setup Wizard', () => {

  test('setup wizard creates multiple metrics', async ({ page }) => {
    await setupUser(page, 'wizardtest');
    const orgName = `Wizard Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Use setup endpoint to create multiple metrics
    const setupResponse = await page.request.post(
      `/api/v1/dashboard/metrics/setup`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          metrics: [
            { name: 'Active Members', value_type: 'number', frequency: 'monthly' },
            { name: 'Monthly Revenue', value_type: 'currency', frequency: 'monthly' },
            { name: 'Retention Rate', value_type: 'percent', frequency: 'quarterly' }
          ]
        }
      }
    );

    expect(setupResponse.status()).toBe(200);
    const result = await setupResponse.json();
    expect(result.metrics_created).toBe(3);
    expect(result.metrics.length).toBe(3);

    // Verify all metrics were created
    const listResponse = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const list = await listResponse.json();
    expect(list.items.length).toBe(3);

    // Check metric types
    const types = list.items.map(m => m.value_type).sort();
    expect(types).toEqual(['currency', 'number', 'percent']);
  });

});


// ============================================================================
// METRIC UPDATE/DELETE TESTS
// ============================================================================

test.describe('Dashboard Metrics: Update and Delete', () => {

  test('can update metric details', async ({ page }) => {
    await setupUser(page, 'metricupdate');
    const orgName = `Update Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Create metric
    const createResponse = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          name: 'Original Name',
          value_type: 'number',
          frequency: 'monthly'
        }
      }
    );
    const metric = await createResponse.json();

    // Update metric
    const updateResponse = await page.request.put(
      `/api/v1/dashboard/metrics/${metric.id}?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          name: 'Updated Name',
          description: 'New description',
          target_value: 100
        }
      }
    );

    expect(updateResponse.status()).toBe(200);
    const updated = await updateResponse.json();
    expect(updated.name).toBe('Updated Name');
    expect(updated.description).toBe('New description');
    expect(parseFloat(updated.target_value)).toBe(100);
  });

  test('can delete metric', async ({ page }) => {
    await setupUser(page, 'metricdelete');
    const orgName = `Delete Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Create metric
    const createResponse = await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          name: 'To Delete',
          value_type: 'number',
          frequency: 'monthly'
        }
      }
    );
    const metric = await createResponse.json();

    // Add a value
    await page.request.post(
      `/api/v1/dashboard/metrics/${metric.id}/values?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: { value: 50, effective_date: formatDate(new Date()) }
      }
    );

    // Delete metric
    const deleteResponse = await page.request.delete(
      `/api/v1/dashboard/metrics/${metric.id}?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    expect(deleteResponse.status()).toBe(204);

    // Verify metric is gone
    const listResponse = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const list = await listResponse.json();
    expect(list.items.length).toBe(0);
  });

});


// ============================================================================
// VALUE TYPE FORMATTING TESTS
// ============================================================================

test.describe('Dashboard Metrics: Value Types', () => {

  test('different value types are stored correctly', async ({ page }) => {
    await setupUser(page, 'valuetypes');
    const orgName = `Value Types Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    // Create metrics of each type
    const types = [
      { name: 'Number Metric', value_type: 'number', testValue: 1234 },
      { name: 'Currency Metric', value_type: 'currency', testValue: 9999.99 },
      { name: 'Percent Metric', value_type: 'percent', testValue: 75 }
    ];

    for (const t of types) {
      const metricResp = await page.request.post(
        `/api/v1/dashboard/metrics`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
          data: {
            organization_id: orgId,
            name: t.name,
            value_type: t.value_type,
            frequency: 'monthly'
          }
        }
      );
      const metric = await metricResp.json();

      await page.request.post(
        `/api/v1/dashboard/metrics/${metric.id}/values?organization_id=${orgId}`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
          data: { value: t.testValue, effective_date: formatDate(new Date()) }
        }
      );
    }

    // Verify all metrics
    const listResponse = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const list = await listResponse.json();
    expect(list.items.length).toBe(3);

    // Check each metric has correct type and value
    const numberMetric = list.items.find(m => m.value_type === 'number');
    const currencyMetric = list.items.find(m => m.value_type === 'currency');
    const percentMetric = list.items.find(m => m.value_type === 'percent');

    expect(parseFloat(numberMetric.latest_value.value)).toBe(1234);
    expect(parseFloat(currencyMetric.latest_value.value)).toBe(9999.99);
    expect(parseFloat(percentMetric.latest_value.value)).toBe(75);
  });

});


// ============================================================================
// PERMISSION TESTS
// ============================================================================

test.describe('Dashboard Metrics: Permissions', () => {

  test('non-member cannot access org metrics', async ({ page }) => {
    // Create user and org
    await setupUser(page, 'metricsowner');
    const orgName = `Permission Test Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);
    const ownerToken = await getAuthToken(page);

    // Create a metric
    await page.request.post(
      `/api/v1/dashboard/metrics`,
      {
        headers: { 'Authorization': `Bearer ${ownerToken}` },
        data: {
          organization_id: orgId,
          name: 'Owner Metric',
          value_type: 'number',
          frequency: 'monthly'
        }
      }
    );

    // Logout and create new user
    await page.evaluate(() => {
      localStorage.clear();
    });
    await setupUser(page, 'nonmember');
    const nonMemberToken = await getAuthToken(page);

    // Try to access org metrics - should fail
    const response = await page.request.get(
      `/api/v1/dashboard/metrics?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${nonMemberToken}` } }
    );

    expect(response.status()).toBe(403);
  });

});
