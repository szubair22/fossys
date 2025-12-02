// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Comprehensive tests for the Organization Details page
 * Tests: page loading, settings tab, danger zone visibility, delete functionality
 */

test.describe('Organization Details Page', () => {
  // Test user - will be created fresh for each test
  let testUserEmail;
  let testUserPassword = 'TestPassword123';
  let testOrgName;
  let testOrgId;

  test.beforeEach(async ({ page }) => {
    // Generate unique credentials for this test run
    testUserEmail = `orgdetails_${Date.now()}@example.com`;
    testOrgName = `Test Org ${Date.now()}`;

    // Register user
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    // Fill registration form
    const nameInput = page.locator('#name');
    if (await nameInput.isVisible()) {
      await nameInput.fill('Test User');
    }

    await page.fill('#email', testUserEmail);
    await page.fill('#password', testUserPassword);

    const confirmPassword = page.locator('#passwordConfirm');
    if (await confirmPassword.isVisible()) {
      await confirmPassword.fill(testUserPassword);
    }

    // Submit and wait for redirect
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForTimeout(3000)
    ]);

    // Check if registration succeeded by trying to login
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#email, input[type="email"]', testUserEmail);
    await page.fill('#password, input[type="password"]', testUserPassword);

    // Submit login
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // We should be redirected to dashboard or organizations
    const currentUrl = page.url();
    console.log('After login, URL:', currentUrl);

    // Navigate to organizations
    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
  });

  test('should load organization details page with all sections', async ({ page }) => {
    // First create an organization
    const createButton = page.locator('button:has-text("Create"), button:has-text("New Organization")').first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);
    }

    // Fill organization name
    const orgNameInput = page.locator('#org-name, input[name="name"]').first();
    if (await orgNameInput.isVisible()) {
      await orgNameInput.fill(testOrgName);

      // Submit
      const submitBtn = page.locator('button[type="submit"], button:has-text("Create")');
      await submitBtn.first().click();
      await page.waitForTimeout(3000);
    }

    // Click on the organization to view details
    const orgLink = page.locator(`a:has-text("${testOrgName}")`).first();

    if (await orgLink.isVisible()) {
      await orgLink.click();
      await page.waitForTimeout(3000);

      // Capture console logs
      page.on('console', msg => {
        if (msg.type() === 'error') {
          console.log('Browser console error:', msg.text());
        }
      });

      // Verify we're on the organization details page
      expect(page.url()).toContain('organization.html');

      // Wait for the page to load
      await page.waitForTimeout(2000);

      // Check that organization header is populated (not showing skeleton)
      const orgHeader = page.locator('#org-header');
      const headerContent = await orgHeader.innerHTML();
      console.log('Organization header HTML:', headerContent.substring(0, 500));

      // The header should not have "animate-pulse" (loading skeleton)
      const hasLoadingSkeleton = headerContent.includes('animate-pulse');
      console.log('Header has loading skeleton:', hasLoadingSkeleton);

      // Organization name should be visible
      const orgNameVisible = await page.locator(`text="${testOrgName}"`).isVisible().catch(() => false);
      console.log('Organization name visible:', orgNameVisible);

      // Check tabs are present
      await expect(page.locator('button:has-text("Overview")')).toBeVisible();
      await expect(page.locator('button:has-text("Members")')).toBeVisible();
      await expect(page.locator('button:has-text("Documents")')).toBeVisible();
      await expect(page.locator('button:has-text("Settings")')).toBeVisible();
    }
  });

  test('should show Danger Zone in Settings tab for organization owner', async ({ page }) => {
    // Create organization
    const createButton = page.locator('button:has-text("Create"), button:has-text("New Organization")').first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);
    }

    const orgNameInput = page.locator('#org-name, input[name="name"]').first();
    if (await orgNameInput.isVisible()) {
      await orgNameInput.fill(testOrgName);
      const submitBtn = page.locator('button[type="submit"], button:has-text("Create")');
      await submitBtn.first().click();
      await page.waitForTimeout(3000);
    }

    // Navigate to org details
    const orgLink = page.locator(`a:has-text("${testOrgName}")`).first();
    if (await orgLink.isVisible()) {
      await orgLink.click();
      await page.waitForTimeout(3000);

      // Click on Settings tab
      const settingsTab = page.locator('button:has-text("Settings")');
      await settingsTab.click();
      await page.waitForTimeout(1000);

      // Check if Settings tab is now active
      const settingsContent = page.locator('#tab-settings');
      await expect(settingsContent).toBeVisible();

      // Check for danger zone
      const dangerZone = page.locator('#danger-zone');
      const isDangerZoneVisible = await dangerZone.isVisible();
      console.log('Danger zone visible:', isDangerZoneVisible);

      // Get danger zone classes to see if it's hidden
      const dangerZoneClasses = await dangerZone.getAttribute('class');
      console.log('Danger zone classes:', dangerZoneClasses);

      // Check for delete button specifically
      const deleteButton = page.locator('button:has-text("Delete Organization")');
      const isDeleteButtonVisible = await deleteButton.isVisible().catch(() => false);
      console.log('Delete button visible:', isDeleteButtonVisible);

      // Take a screenshot for debugging
      await page.screenshot({ path: 'test-results/settings-tab-screenshot.png', fullPage: true });

      // The danger zone should be visible for the owner
      expect(isDangerZoneVisible).toBeTruthy();
    }
  });

  test('should successfully delete an organization', async ({ page }) => {
    // Create organization
    const createButton = page.locator('button:has-text("Create"), button:has-text("New Organization")').first();

    if (await createButton.isVisible()) {
      await createButton.click();
      await page.waitForTimeout(500);
    }

    const deleteOrgName = `Delete Test ${Date.now()}`;
    const orgNameInput = page.locator('#org-name, input[name="name"]').first();

    if (await orgNameInput.isVisible()) {
      await orgNameInput.fill(deleteOrgName);
      const submitBtn = page.locator('button[type="submit"], button:has-text("Create")');
      await submitBtn.first().click();
      await page.waitForTimeout(3000);
    }

    // Navigate to org details
    const orgLink = page.locator(`a:has-text("${deleteOrgName}")`).first();
    if (await orgLink.isVisible()) {
      await orgLink.click();
      await page.waitForTimeout(3000);

      // Capture the org ID from URL for verification
      const url = page.url();
      const idMatch = url.match(/id=([^&]+)/);
      const orgId = idMatch ? idMatch[1] : null;
      console.log('Organization ID:', orgId);

      // Click on Settings tab
      const settingsTab = page.locator('button:has-text("Settings")');
      await settingsTab.click();
      await page.waitForTimeout(1000);

      // Handle dialog
      page.on('dialog', async dialog => {
        console.log('Dialog appeared:', dialog.message());
        await dialog.accept();
      });

      // Click delete button
      const deleteButton = page.locator('button:has-text("Delete Organization")');
      if (await deleteButton.isVisible()) {
        console.log('Clicking delete button...');

        // Capture console errors
        page.on('console', msg => {
          console.log(`Browser ${msg.type()}:`, msg.text());
        });

        await deleteButton.click();
        await page.waitForTimeout(5000);

        // Should be redirected to organizations list
        const finalUrl = page.url();
        console.log('After delete, URL:', finalUrl);

        // Verify redirect happened
        expect(finalUrl).toContain('organizations.html');

        // Verify organization no longer exists
        const deletedOrgVisible = await page.locator(`text="${deleteOrgName}"`).isVisible().catch(() => false);
        console.log('Deleted org still visible:', deletedOrgVisible);
        expect(deletedOrgVisible).toBeFalsy();
      } else {
        console.log('Delete button not visible!');
        await page.screenshot({ path: 'test-results/delete-button-not-visible.png', fullPage: true });
      }
    }
  });

  test('should check API responses for debugging', async ({ page, request }) => {
    // Test organizations API directly
    const orgsResponse = await request.get('/api/collections/organizations/records');
    console.log('Organizations API status:', orgsResponse.status());
    const orgsData = await orgsResponse.json();
    console.log('Organizations count:', orgsData.totalItems);

    // Test users API
    const usersResponse = await request.get('/api/collections/users/records');
    console.log('Users API status:', usersResponse.status());
    const usersData = await usersResponse.json();
    console.log('Users count:', usersData.totalItems);

    // Test ai_integrations API
    const aiResponse = await request.get('/api/collections/ai_integrations/records');
    console.log('AI Integrations API status:', aiResponse.status());

    // Test org_memberships API
    const membershipsResponse = await request.get('/api/collections/org_memberships/records');
    console.log('Org Memberships API status:', membershipsResponse.status());

    expect(orgsResponse.status()).toBe(200);
    expect(usersResponse.status()).toBe(200);
    expect(aiResponse.status()).toBe(200);
    expect(membershipsResponse.status()).toBe(200);
  });
});

test.describe('Console Error Debugging', () => {
  test('should capture all console errors on organization page', async ({ page }) => {
    const errors = [];
    const logs = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
      logs.push(`[${msg.type()}] ${msg.text()}`);
    });

    page.on('pageerror', error => {
      errors.push(`Page error: ${error.message}`);
    });

    // Register and login
    const email = `console_test_${Date.now()}@example.com`;
    const password = 'TestPassword123';

    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#name', 'Console Test User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Login
    await page.goto('/pages/login.html');
    await page.fill('#email, input[type="email"]', email);
    await page.fill('#password, input[type="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Go to organizations
    await page.goto('/pages/organizations.html');
    await page.waitForTimeout(3000);

    console.log('=== Console logs on organizations page ===');
    logs.forEach(log => console.log(log));

    console.log('=== Errors captured ===');
    errors.forEach(err => console.log('ERROR:', err));

    // Clear for next page
    logs.length = 0;
    errors.length = 0;

    // Create an org
    const createBtn = page.locator('button:has-text("Create")').first();
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(500);

      const orgName = `Console Debug ${Date.now()}`;
      await page.fill('#org-name, input[name="name"]', orgName);
      await page.locator('button[type="submit"], button:has-text("Create")').first().click();
      await page.waitForTimeout(3000);

      // Navigate to org details
      const orgLink = page.locator(`a:has-text("${orgName}")`).first();
      if (await orgLink.isVisible()) {
        await orgLink.click();
        await page.waitForTimeout(5000);

        console.log('=== Console logs on organization details page ===');
        logs.forEach(log => console.log(log));

        console.log('=== Errors on organization details page ===');
        errors.forEach(err => console.log('ERROR:', err));
      }
    }

    // Report any errors found
    if (errors.length > 0) {
      console.log('\n!!! Found browser errors that need fixing !!!');
    }
  });
});
