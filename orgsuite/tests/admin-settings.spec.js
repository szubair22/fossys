// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * ADMIN SETTINGS E2E TESTS
 *
 * Tests for:
 * - Organization-level admin settings (governance, membership, finance)
 * - Access control (admin vs non-admin users)
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

test.describe('Admin Settings: Governance Setup', () => {
  test('org admin can view and update governance settings', async ({ page }) => {
    // Setup user and create organization
    await setupUser(page, 'govadmin');
    const orgName = `Gov Settings Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Navigate to governance settings
    await page.goto('/pages/admin_governance.html');
    await page.waitForLoadState('networkidle');

    // Wait for org selector to load
    await page.waitForSelector('#org-selector option:not([value=""])');

    // Select the organization
    const selector = page.locator('#org-selector');
    await selector.selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Verify form is populated with defaults
    const durationInput = page.locator('#setting-duration');
    await expect(durationInput).toBeVisible();

    // Get current value
    const currentDuration = await durationInput.inputValue();
    console.log('Current duration:', currentDuration);

    // Change meeting duration
    await durationInput.fill('90');

    // Change quorum settings
    await page.locator('#setting-quorum-type').selectOption('count');
    await page.locator('#setting-quorum-value').fill('5');

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
    await selector.selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Verify settings were saved
    const savedDuration = await page.locator('#setting-duration').inputValue();
    expect(savedDuration).toBe('90');

    const savedQuorumType = await page.locator('#setting-quorum-type').inputValue();
    expect(savedQuorumType).toBe('count');
  });

  test('org admin can manage motion types', async ({ page }) => {
    await setupUser(page, 'motiontype');
    const orgName = `Motion Types Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_governance.html');
    await page.waitForLoadState('networkidle');

    // Wait for org selector and select org
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Add a custom motion type
    await page.locator('#new-motion-type').fill('Emergency Motion');
    await page.locator('button:has-text("Add")').first().click();

    // Verify the chip was added
    const motionTypesContainer = page.locator('#motion-types-container');
    await expect(motionTypesContainer).toContainText('Emergency Motion');

    // Save settings
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );
    await page.waitForTimeout(500);

    // Reload and verify
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    await expect(page.locator('#motion-types-container')).toContainText('Emergency Motion');
  });
});

test.describe('Admin Settings: Membership Setup', () => {
  test('org admin can add member types', async ({ page }) => {
    await setupUser(page, 'membertype');
    const orgName = `Member Types Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_membership.html');
    await page.waitForLoadState('networkidle');

    // Wait for org selector and select org
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Add a custom member type
    await page.locator('#new-member-type').fill('Volunteer Leader');
    await page.locator('button:has-text("Add")').first().click();

    // Verify the chip was added
    await expect(page.locator('#member-types-container')).toContainText('Volunteer Leader');

    // Save settings
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );
    await page.waitForTimeout(500);

    // Reload and verify persistence
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    await expect(page.locator('#member-types-container')).toContainText('Volunteer Leader');
  });

  test('org admin can configure required fields', async ({ page }) => {
    await setupUser(page, 'reqfields');
    const orgName = `Required Fields Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_membership.html');
    await page.waitForLoadState('networkidle');

    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Enable required email
    const emailCheckbox = page.locator('#setting-require-email');
    await emailCheckbox.check();
    expect(await emailCheckbox.isChecked()).toBe(true);

    // Save
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );

    // Reload and verify
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    expect(await page.locator('#setting-require-email').isChecked()).toBe(true);
  });
});

test.describe('Admin Settings: Finance Setup', () => {
  test('org admin can configure fiscal year and currency', async ({ page }) => {
    await setupUser(page, 'finsetup');
    const orgName = `Finance Settings Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');

    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Change fiscal year start
    await page.locator('#setting-fiscal-month').selectOption('7'); // July

    // Change currency
    await page.locator('#setting-currency').selectOption('EUR');

    // Save
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );
    await page.waitForTimeout(500);

    // Reload and verify
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    expect(await page.locator('#setting-fiscal-month').inputValue()).toBe('7');
    expect(await page.locator('#setting-currency').inputValue()).toBe('EUR');
  });

  test('org admin can add payment methods', async ({ page }) => {
    await setupUser(page, 'paymethod');
    const orgName = `Payment Methods Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_finance.html');
    await page.waitForLoadState('networkidle');

    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Add a custom payment method
    await page.locator('#new-payment-method').fill('Cryptocurrency');
    await page.locator('button:has-text("Add")').first().click();

    await expect(page.locator('#payment-methods-container')).toContainText('Cryptocurrency');

    // Save
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );
  });
});

test.describe('Admin Settings: General Org Settings', () => {
  test('org admin can configure timezone and locale', async ({ page }) => {
    await setupUser(page, 'orggeneral');
    const orgName = `General Settings Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/admin_org_settings.html');
    await page.waitForLoadState('networkidle');

    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    // Change timezone
    await page.locator('#setting-timezone').selectOption('America/New_York');

    // Change locale
    await page.locator('#setting-locale').selectOption('en-GB');

    // Save
    await page.locator('#save-settings-btn').click();
    await page.waitForResponse(resp =>
      resp.url().includes('/api/v1/admin/org-settings')
    );
    await page.waitForTimeout(500);

    // Reload and verify
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#org-selector option:not([value=""])');
    await page.locator('#org-selector').selectOption({ label: orgName });
    await page.waitForTimeout(1500);

    expect(await page.locator('#setting-timezone').inputValue()).toBe('America/New_York');
    expect(await page.locator('#setting-locale').inputValue()).toBe('en-GB');
  });
});

test.describe('Admin Settings: Access Control', () => {
  test('admin menu is visible in navigation', async ({ page }) => {
    await setupUser(page, 'adminmenu');
    const orgName = `Admin Menu Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // Go to dashboard
    await page.goto('/pages/dashboard.html');
    await page.waitForLoadState('networkidle');

    // Check that Admin menu exists in navigation
    const adminMenu = page.locator('#admin-menu');
    await expect(adminMenu).toBeVisible();
  });

  test('non-admin user sees restricted message on org settings', async ({ page }) => {
    await setupUser(page, 'nonadmin');

    // Don't create an org, so user has no admin access
    await page.goto('/pages/admin_org_settings.html');
    await page.waitForLoadState('networkidle');

    // Org selector should indicate no orgs with admin access
    const selector = page.locator('#org-selector');
    await page.waitForTimeout(1000);
    const selectorText = await selector.textContent();

    // Should indicate no admin access
    expect(selectorText).toContain('No organizations with admin access');
  });
});
