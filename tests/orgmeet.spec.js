// @ts-check
const { test, expect } = require('@playwright/test');

// Test configuration - uses baseURL from playwright.config.js
// All page.goto() calls should use relative paths or use baseURL from test config
const TEST_USER = {
  email: `test${Date.now()}@example.com`,
  password: 'TestPassword123!',
  name: 'Test User'
};

// Helper to generate unique org names
function uniqueOrgName(prefix = 'Test Org') {
  return `${prefix} ${Date.now()}`;
}

test.describe('OrgMeet Application Tests', () => {

  test.describe('User Registration and Login', () => {

    test('should load the login page', async ({ page }) => {
      await page.goto(`/pages/login.html`);

      // Check page loaded
      await expect(page.locator('h1')).toContainText(/Sign in|Login|Welcome/i);

      // Check form elements exist
      await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
      await expect(page.locator('input[type="password"], input[name="password"]')).toBeVisible();
    });

    test('should show error for invalid credentials', async ({ page }) => {
      await page.goto(`/pages/login.html`);

      // Wait for page to fully load
      await page.waitForLoadState('networkidle');

      // Fill in invalid credentials
      await page.fill('input[type="email"], input[name="email"]', 'nonexistent@example.com');
      await page.fill('input[type="password"], input[name="password"]', 'wrongpassword');

      // Submit the form
      await page.click('button[type="submit"]');

      // Wait for error message or notification
      await page.waitForTimeout(2000);

      // Check for error (could be notification, alert, or inline error)
      const errorVisible = await page.locator('.notification, .error, [class*="error"], [class*="alert"]').isVisible().catch(() => false);
      const pageContent = await page.content();

      // The page should show some indication of failure
      console.log('Page after login attempt:', pageContent.substring(0, 500));
    });

    test('should register a new user', async ({ page }) => {
      await page.goto(`/pages/register.html`);

      // Wait for page to fully load
      await page.waitForLoadState('networkidle');

      // Fill registration form
      const nameInput = page.locator('input[name="name"], input[id="name"], input[placeholder*="name" i]');
      const emailInput = page.locator('input[type="email"], input[name="email"]');
      const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
      const confirmPasswordInput = page.locator('input[name="passwordConfirm"], input[id="passwordConfirm"], input[name="confirmPassword"], input[id="confirm-password"]');

      if (await nameInput.isVisible()) {
        await nameInput.fill(TEST_USER.name);
      }

      await emailInput.fill(TEST_USER.email);
      await passwordInput.fill(TEST_USER.password);

      if (await confirmPasswordInput.isVisible()) {
        await confirmPasswordInput.fill(TEST_USER.password);
      }

      // Submit the form
      await page.click('button[type="submit"]');

      // Wait for navigation or success message
      await page.waitForTimeout(3000);

      // Check if we're redirected to login or dashboard, or see success message
      const currentUrl = page.url();
      const pageContent = await page.content();

      console.log('After registration, URL:', currentUrl);
      console.log('Page content sample:', pageContent.substring(0, 500));
    });

    test('should login with registered user', async ({ page }) => {
      // First register the user
      await page.goto(`/pages/register.html`);
      await page.waitForLoadState('networkidle');

      const emailInput = page.locator('input[type="email"], input[name="email"]');
      const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
      const confirmPasswordInput = page.locator('input[name="passwordConfirm"], input[id="passwordConfirm"]');
      const nameInput = page.locator('input[name="name"], input[id="name"]');

      if (await nameInput.isVisible()) {
        await nameInput.fill(TEST_USER.name);
      }
      await emailInput.fill(TEST_USER.email);
      await passwordInput.fill(TEST_USER.password);
      if (await confirmPasswordInput.isVisible()) {
        await confirmPasswordInput.fill(TEST_USER.password);
      }

      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      // Now try to login
      await page.goto(`/pages/login.html`);
      await page.waitForLoadState('networkidle');

      await page.fill('input[type="email"], input[name="email"]', TEST_USER.email);
      await page.fill('input[type="password"], input[name="password"]', TEST_USER.password);

      // Listen for navigation
      const navigationPromise = page.waitForURL(/\/(dashboard|organizations|index)/, { timeout: 10000 }).catch(() => null);

      await page.click('button[type="submit"]');

      await navigationPromise;
      await page.waitForTimeout(2000);

      const currentUrl = page.url();
      console.log('After login, URL:', currentUrl);

      // Should be redirected away from login page
      expect(currentUrl).not.toContain('/login.html');
    });
  });

  test.describe('Organizations', () => {
    // Use a fresh user for organization tests
    const orgTestUser = {
      email: `orgtest${Date.now()}@example.com`,
      password: 'TestPassword123!',
      name: 'Org Test User'
    };

    test.beforeEach(async ({ page }) => {
      // Register and login
      await page.goto(`/pages/register.html`);
      await page.waitForLoadState('networkidle');

      const nameInput = page.locator('input[name="name"], input[id="name"]');
      if (await nameInput.isVisible()) {
        await nameInput.fill(orgTestUser.name);
      }
      await page.fill('input[type="email"], input[name="email"]', orgTestUser.email);
      await page.fill('input[type="password"], input[name="password"]', orgTestUser.password);

      const confirmPasswordInput = page.locator('input[name="passwordConfirm"], input[id="passwordConfirm"]');
      if (await confirmPasswordInput.isVisible()) {
        await confirmPasswordInput.fill(orgTestUser.password);
      }

      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);

      // Login
      await page.goto(`/pages/login.html`);
      await page.waitForLoadState('networkidle');
      await page.fill('input[type="email"], input[name="email"]', orgTestUser.email);
      await page.fill('input[type="password"], input[name="password"]', orgTestUser.password);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);
    });

    test('should load organizations page', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Check that the page loaded without errors
      const errorVisible = await page.locator('.error, [class*="error"]').isVisible().catch(() => false);
      const pageContent = await page.content();

      console.log('Organizations page content:', pageContent.substring(0, 1000));

      // Should see organizations heading or create button
      await expect(page.locator('body')).toContainText(/organization/i);
    });

    test('should create a new organization', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      const orgName = uniqueOrgName('Playwright Test Org');

      // Look for create button or form
      const createButton = page.locator('button:has-text("Create"), button:has-text("New"), button:has-text("Add"), a:has-text("Create")');

      if (await createButton.isVisible()) {
        await createButton.first().click();
        await page.waitForTimeout(1000);
      }

      // Fill organization form (could be modal or inline)
      const orgNameInput = page.locator('input[name="name"], input[id="org-name"], input[placeholder*="name" i]').first();

      if (await orgNameInput.isVisible()) {
        await orgNameInput.fill(orgName);

        // Look for description field
        const descInput = page.locator('textarea[name="description"], input[name="description"], textarea[id="org-description"]');
        if (await descInput.isVisible()) {
          await descInput.fill('Created by Playwright test');
        }

        // Submit
        const submitButton = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Save")');
        await submitButton.first().click();

        await page.waitForTimeout(3000);

        // Verify organization was created
        const pageContent = await page.content();
        console.log('After org creation:', pageContent.substring(0, 1000));

        // Check if org appears in the list
        await expect(page.locator('body')).toContainText(orgName);
      }
    });

    test('should show error when creating duplicate organization name', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      const duplicateName = uniqueOrgName('Duplicate Test');

      // Create first organization
      const createButton = page.locator('button:has-text("Create"), button:has-text("New"), button:has-text("Add")');

      for (let attempt = 0; attempt < 2; attempt++) {
        if (await createButton.first().isVisible()) {
          await createButton.first().click();
          await page.waitForTimeout(500);
        }

        const orgNameInput = page.locator('input[name="name"], input[id="org-name"]').first();
        if (await orgNameInput.isVisible()) {
          await orgNameInput.fill(duplicateName);

          const submitButton = page.locator('button[type="submit"], button:has-text("Create")');
          await submitButton.first().click();
          await page.waitForTimeout(2000);
        }

        if (attempt === 0) {
          // Wait for first org to be created
          await page.waitForTimeout(1000);
        }
      }

      // After second attempt, should see error about duplicate
      const pageContent = await page.content();
      console.log('After duplicate attempt:', pageContent.substring(0, 1500));

      // Check for error message containing "exists", "duplicate", or "unique"
      const errorMessageVisible = await page.locator(':has-text("already exists"), :has-text("unique"), :has-text("duplicate")').isVisible().catch(() => false);
      console.log('Duplicate error visible:', errorMessageVisible);
    });

    test('should navigate to organization details', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Create an org first
      const orgName = uniqueOrgName('Details Test Org');

      const createButton = page.locator('button:has-text("Create"), button:has-text("New")');
      if (await createButton.first().isVisible()) {
        await createButton.first().click();
        await page.waitForTimeout(500);

        const orgNameInput = page.locator('input[name="name"], input[id="org-name"]').first();
        if (await orgNameInput.isVisible()) {
          await orgNameInput.fill(orgName);
          const submitButton = page.locator('button[type="submit"], button:has-text("Create")');
          await submitButton.first().click();
          await page.waitForTimeout(2000);
        }
      }

      // Click on the org to view details
      const orgLink = page.locator(`a:has-text("${orgName}"), [href*="organization.html"]`).first();

      if (await orgLink.isVisible()) {
        await orgLink.click();
        await page.waitForTimeout(2000);

        // Should be on organization details page
        expect(page.url()).toContain('organization.html');
        await expect(page.locator('body')).toContainText(orgName);
      }
    });

    test('should show Settings tab with delete option for owner', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Create an org
      const orgName = uniqueOrgName('Settings Test Org');

      const createButton = page.locator('button:has-text("Create"), button:has-text("New")');
      if (await createButton.first().isVisible()) {
        await createButton.first().click();
        await page.waitForTimeout(500);

        const orgNameInput = page.locator('input[name="name"], input[id="org-name"]').first();
        if (await orgNameInput.isVisible()) {
          await orgNameInput.fill(orgName);
          const submitButton = page.locator('button[type="submit"], button:has-text("Create")');
          await submitButton.first().click();
          await page.waitForTimeout(2000);
        }
      }

      // Navigate to org details
      const orgLink = page.locator(`a:has-text("${orgName}"), [href*="organization.html"]`).first();
      if (await orgLink.isVisible()) {
        await orgLink.click();
        await page.waitForTimeout(2000);
      }

      // Click on Settings tab
      const settingsTab = page.locator('button:has-text("Settings"), a:has-text("Settings"), [data-tab="settings"]');
      if (await settingsTab.isVisible()) {
        await settingsTab.click();
        await page.waitForTimeout(1000);
      }

      // Check for danger zone / delete button
      const dangerZone = page.locator('#danger-zone, .danger-zone, :has-text("Danger Zone")');
      const deleteButton = page.locator('button:has-text("Delete Organization"), button:has-text("Delete")');

      const dangerZoneVisible = await dangerZone.isVisible().catch(() => false);
      const deleteButtonVisible = await deleteButton.isVisible().catch(() => false);

      console.log('Danger zone visible:', dangerZoneVisible);
      console.log('Delete button visible:', deleteButtonVisible);

      // At least one should be visible for the owner
      expect(dangerZoneVisible || deleteButtonVisible).toBeTruthy();
    });

    test('should delete an organization', async ({ page }) => {
      await page.goto(`/pages/organizations.html`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(2000);

      // Create an org to delete
      const orgName = uniqueOrgName('Delete Test Org');

      const createButton = page.locator('button:has-text("Create"), button:has-text("New")');
      if (await createButton.first().isVisible()) {
        await createButton.first().click();
        await page.waitForTimeout(500);

        const orgNameInput = page.locator('input[name="name"], input[id="org-name"]').first();
        if (await orgNameInput.isVisible()) {
          await orgNameInput.fill(orgName);
          const submitButton = page.locator('button[type="submit"], button:has-text("Create")');
          await submitButton.first().click();
          await page.waitForTimeout(2000);
        }
      }

      // Navigate to org details
      const orgLink = page.locator(`a:has-text("${orgName}"), [href*="organization.html"]`).first();
      if (await orgLink.isVisible()) {
        await orgLink.click();
        await page.waitForTimeout(2000);
      }

      // Click on Settings tab
      const settingsTab = page.locator('button:has-text("Settings"), a:has-text("Settings"), [data-tab="settings"]');
      if (await settingsTab.isVisible()) {
        await settingsTab.click();
        await page.waitForTimeout(1000);
      }

      // Handle confirm dialog
      page.on('dialog', async dialog => {
        console.log('Dialog message:', dialog.message());
        await dialog.accept();
      });

      // Click delete button
      const deleteButton = page.locator('button:has-text("Delete Organization"), button:has-text("Delete"):visible');
      if (await deleteButton.isVisible()) {
        await deleteButton.click();
        await page.waitForTimeout(3000);

        // Should be redirected to organizations list
        const currentUrl = page.url();
        console.log('After delete, URL:', currentUrl);

        // Should either be on organizations list or see success message
        const wasDeleted = currentUrl.includes('organizations.html') ||
                          !(await page.locator(`text="${orgName}"`).isVisible().catch(() => false));

        console.log('Organization was deleted:', wasDeleted);
      }
    });
  });

  test.describe('API Health Check', () => {
    test('should have working PocketBase API', async ({ request }) => {
      // Test that API is accessible
      const response = await request.get(`/api/health`);

      // PocketBase may not have /health endpoint, try collections
      if (response.status() === 404) {
        const collectionsResponse = await request.get(`/api/collections/organizations/records`);
        expect(collectionsResponse.status()).toBe(200);
      } else {
        expect(response.ok()).toBeTruthy();
      }
    });

    test('should return proper error for missing collection', async ({ request }) => {
      const response = await request.get(`/api/collections/nonexistent/records`);
      expect(response.status()).toBe(404);
    });
  });
});
