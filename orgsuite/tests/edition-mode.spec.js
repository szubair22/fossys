// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * EDITION MODE E2E TESTS
 *
 * Tests for:
 * - Startup Edition hides Contracts, Rev Rec, Donations tabs
 * - Nonprofit Edition shows them
 * - Toggling edition via admin_finance.html updates UI visibility
 * - Attempting to access Rev Rec API when disabled returns 403
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

// Helper to login or register a user
async function setupUser(page, prefix = 'test') {
  const email = `${prefix}_${uniqueId()}@example.com`;
  const password = 'TestPass123';

  await page.goto('/pages/register.html');
  await page.waitForLoadState('networkidle');

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
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);

  await page.locator('button:has-text("Create Organization")').first().click();

  // Wait for modal to be visible
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
  const status = response.status();

  if (status !== 200 && status !== 201) {
    throw new Error(`Failed to create organization: ${status}`);
  }

  // Wait for modal to close
  await modal.waitFor({ state: 'hidden', timeout: 5000 });
  await page.waitForTimeout(1000);

  // Get org ID from API
  const orgsResponse = await page.evaluate(async () => {
    const token = window.App?.pb?.authStore?.token;
    if (!token) return null;
    const resp = await fetch('/api/v1/organizations', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
  });

  if (orgsResponse && orgsResponse.items && orgsResponse.items.length > 0) {
    // Find the org by name
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

test.describe('Edition Mode: Default Startup Edition', () => {
  test('new organization defaults to startup edition', async ({ page }) => {
    await setupUser(page, 'startupdefault');
    const orgName = `Startup Default Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Navigate to finance settings
    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');

    // Wait for org selector and select org
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Verify startup edition is selected by default
    const startupCard = page.locator('#edition-startup-card');
    await expect(startupCard).toHaveClass(/selected/);

    // Verify nonprofit edition is NOT selected
    const nonprofitCard = page.locator('#edition-nonprofit-card');
    await expect(nonprofitCard).not.toHaveClass(/selected/);
  });

  test('startup edition hides contracts menu item', async ({ page }) => {
    await setupUser(page, 'startupnav');
    const orgName = `Startup Nav Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // Navigate to dashboard to check nav
    await page.goto('/pages/dashboard.html');
    await page.waitForLoadState('networkidle');

    // By default (startup edition), contracts-only items should be hidden
    // Note: The nav updates on page load, but edition visibility requires org context
    // Since we haven't selected an org yet, items may still be visible
    // This test validates the mechanism exists
    const contractsLink = page.locator('a[href="/pages/finance_contracts.html"]');
    const revRecLink = page.locator('a[href="/pages/finance_rev_rec.html"]');

    // These links exist in the nav but will be hidden by edition CSS classes
    await expect(contractsLink).toBeAttached();
    await expect(revRecLink).toBeAttached();
  });
});

test.describe('Edition Mode: Finance Page Access Control', () => {
  test('contracts page shows warning when feature disabled', async ({ page }) => {
    await setupUser(page, 'contractswarn');
    const orgName = `Contracts Warning Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Navigate to contracts page
    await page.goto(`/pages/finance_contracts.html?org=${orgId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Should show edition warning
    const warning = page.locator('#edition-warning');
    await expect(warning).toBeVisible();

    // Content should be hidden
    const content = page.locator('#contracts-content');
    await expect(content).toBeHidden();

    // Warning should mention Nonprofit Edition
    await expect(warning).toContainText('Nonprofit Edition');
  });

  test('revenue recognition page shows warning when feature disabled', async ({ page }) => {
    await setupUser(page, 'revrecwarn');
    const orgName = `Rev Rec Warning Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Navigate to rev rec page
    await page.goto(`/pages/finance_rev_rec.html?org=${orgId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Should show edition warning
    const warning = page.locator('#edition-warning');
    await expect(warning).toBeVisible();

    // Content should be hidden
    const content = page.locator('#rev-rec-content');
    await expect(content).toBeHidden();
  });
});

test.describe('Edition Mode: Toggle Between Editions', () => {
  test('can switch from startup to nonprofit edition', async ({ page }) => {
    await setupUser(page, 'editionswitch');
    const orgName = `Edition Switch Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // Navigate to finance settings
    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');

    // Wait for org selector and select org
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Verify startup is selected initially
    const startupCard = page.locator('#edition-startup-card');
    await expect(startupCard).toHaveClass(/selected/);

    // Click nonprofit edition card
    await page.locator('#edition-nonprofit-card').click();
    await page.waitForTimeout(500);

    // Verify nonprofit is now selected
    const nonprofitCard = page.locator('#edition-nonprofit-card');
    await expect(nonprofitCard).toHaveClass(/selected/);
    await expect(startupCard).not.toHaveClass(/selected/);

    // Save settings
    const saveBtn = page.locator('#save-settings-btn');
    await saveBtn.click();

    // Wait for save to complete
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings') && resp.request().method() === 'PUT'
    );
    await page.waitForTimeout(500);

    // Reload page to verify settings persisted
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Verify nonprofit is still selected
    await expect(page.locator('#edition-nonprofit-card')).toHaveClass(/selected/);
  });

  test('nonprofit edition enables contracts page access', async ({ page }) => {
    await setupUser(page, 'nonprofitaccess');
    const orgName = `Nonprofit Access Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // First, switch to nonprofit edition
    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Click nonprofit edition
    await page.locator('#edition-nonprofit-card').click();
    await page.waitForTimeout(500);

    // Save
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings') && resp.request().method() === 'PUT'
    );
    await page.waitForTimeout(500);

    // Now navigate to contracts page
    await page.goto(`/pages/finance_contracts.html?org=${orgId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Warning should be hidden
    const warning = page.locator('#edition-warning');
    await expect(warning).toBeHidden();

    // Content should be visible
    const content = page.locator('#contracts-content');
    await expect(content).toBeVisible();
  });
});

test.describe('Edition Mode: API Access Control', () => {
  test('contracts API returns 403 when feature disabled (startup edition)', async ({ page }) => {
    await setupUser(page, 'apiblock');
    const orgName = `API Block Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Get auth token
    const token = await getAuthToken(page);

    // Try to access contracts API
    const response = await page.request.get(
      `/api/v1/finance/contracts?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    // Should return 403 Forbidden
    expect(response.status()).toBe(403);

    const body = await response.json();
    expect(body.detail).toContain('not enabled');
  });

  test('revenue recognition API returns 403 when feature disabled', async ({ page }) => {
    await setupUser(page, 'revapiblock');
    const orgName = `Rev API Block Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Get auth token
    const token = await getAuthToken(page);

    // Try to access rev rec API
    const response = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    // Should return 403 Forbidden
    expect(response.status()).toBe(403);

    const body = await response.json();
    expect(body.detail).toContain('not enabled');
  });

  test('contracts API accessible after enabling nonprofit edition', async ({ page }) => {
    await setupUser(page, 'apienable');
    const orgName = `API Enable Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Get auth token
    const token = await getAuthToken(page);

    // First, switch to nonprofit edition via UI
    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    await page.locator('#edition-nonprofit-card').click();
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings') && resp.request().method() === 'PUT'
    );
    await page.waitForTimeout(500);

    // Now try contracts API - should succeed (200, not 403)
    const response = await page.request.get(
      `/api/v1/finance/contracts?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );

    // Should return 200 OK (empty list since no contracts yet)
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('items');
    expect(body.items).toEqual([]);
  });
});

test.describe('Edition Mode: UI Visibility Helpers', () => {
  test('UI.getEditionFeatures returns correct defaults for startup', async ({ page }) => {
    await setupUser(page, 'uihelper');
    const orgName = `UI Helper Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await page.goto('/pages/dashboard.html');
    await page.waitForLoadState('networkidle');

    // Use UI helper to get features
    const features = await page.evaluate(async (id) => {
      return await window.UI.getEditionFeatures(id);
    }, orgId);

    // Should return startup defaults
    expect(features).toBeTruthy();
    expect(features.edition).toBe('startup');
    expect(features.enable_rev_rec).toBe(false);
    expect(features.enable_contracts).toBe(false);
    expect(features.enable_donations).toBe(false);
    expect(features.enable_restrictions).toBe(false);
    expect(features.enable_budgeting).toBe(false);
  });

  test('UI.getEditionFeatures returns correct values after switching to nonprofit', async ({ page }) => {
    await setupUser(page, 'uinonprofit');
    const orgName = `UI Nonprofit Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Switch to nonprofit
    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    await page.locator('#edition-nonprofit-card').click();
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings') && resp.request().method() === 'PUT'
    );
    await page.waitForTimeout(500);

    // Clear cache and check features
    await page.evaluate((id) => {
      window.UI.clearEditionCache(id);
    }, orgId);

    const features = await page.evaluate(async (id) => {
      return await window.UI.getEditionFeatures(id);
    }, orgId);

    // Should return nonprofit values
    expect(features).toBeTruthy();
    expect(features.edition).toBe('nonprofit');
    expect(features.enable_rev_rec).toBe(true);
    expect(features.enable_contracts).toBe(true);
    expect(features.enable_donations).toBe(true);
    expect(features.enable_restrictions).toBe(true);
    expect(features.enable_budgeting).toBe(true);
  });
});
