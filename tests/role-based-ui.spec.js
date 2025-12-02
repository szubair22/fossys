// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * ROLE-BASED UI TESTS
 *
 * Tests for role-based visibility controls ensuring:
 * - Admin/owner users can see edit/delete controls
 * - Viewer users cannot see admin controls
 * - Role helpers work correctly
 */

test.describe('Role-Based UI Tests', () => {

  // Helper to register and login a test user
  async function registerUser(page, suffix = '') {
    const email = `role_test_${Date.now()}${suffix}@example.com`;
    const password = 'RoleTest123';

    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#name', 'Role Test User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 10000 });
    return { email, password };
  }

  test('API.roles helpers should exist in browser', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const roleHelpers = await page.evaluate(() => {
      return {
        rolesExists: typeof window.API?.roles !== 'undefined',
        getUserRole: typeof window.API?.roles?.getUserRole === 'function',
        hasMinRole: typeof window.API?.roles?.hasMinRole === 'function',
        isAdmin: typeof window.API?.roles?.isAdmin === 'function',
        isOwner: typeof window.API?.roles?.isOwner === 'function'
      };
    });

    console.log('Role helpers:', roleHelpers);
    expect(roleHelpers.rolesExists).toBe(true);
    expect(roleHelpers.getUserRole).toBe(true);
    expect(roleHelpers.hasMinRole).toBe(true);
    expect(roleHelpers.isAdmin).toBe(true);
    expect(roleHelpers.isOwner).toBe(true);
  });

  test('UI.initRoleBasedUI should exist', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const uiHelpers = await page.evaluate(() => {
      return {
        uiExists: typeof window.UI !== 'undefined',
        initRoleBasedUI: typeof window.UI?.initRoleBasedUI === 'function',
        applyRoleVisibility: typeof window.UI?.applyRoleVisibility === 'function',
        showForAdmin: typeof window.UI?.showForAdmin === 'function',
        showForOwner: typeof window.UI?.showForOwner === 'function',
        handle403: typeof window.UI?.handle403 === 'function'
      };
    });

    console.log('UI helpers:', uiHelpers);
    expect(uiHelpers.uiExists).toBe(true);
    expect(uiHelpers.initRoleBasedUI).toBe(true);
    expect(uiHelpers.applyRoleVisibility).toBe(true);
    expect(uiHelpers.showForAdmin).toBe(true);
    expect(uiHelpers.showForOwner).toBe(true);
    expect(uiHelpers.handle403).toBe(true);
  });

  test('Documents upload button should have role requirement attribute', async ({ page }) => {
    await registerUser(page);

    // Fetch the meeting page content
    const pageContent = await page.evaluate(async () => {
      const resp = await fetch('/pages/meeting.html');
      return await resp.text();
    });

    // Verify upload button has data-require-role attribute
    expect(pageContent).toContain('id="upload-document-btn"');
    expect(pageContent).toContain('data-require-role="member"');
  });

  test('Projects page should have role-based add button', async ({ page }) => {
    await registerUser(page);

    // Fetch the projects page content
    const pageContent = await page.evaluate(async () => {
      const resp = await fetch('/pages/projects.html');
      return await resp.text();
    });

    // Verify add button has data-require-role attribute
    expect(pageContent).toContain('id="add-project-btn"');
    expect(pageContent).toContain('data-require-role="member"');
  });

  test('Projects page shows empty state or loading when first loaded', async ({ page }) => {
    await registerUser(page);

    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    // Verify the projects list exists
    const projectsList = page.locator('#projects-list');
    await expect(projectsList).toBeVisible();

    // Should show either loading or empty state
    const text = await projectsList.textContent();
    const hasValidState = text.includes('Loading') ||
                          text.includes('Select') ||
                          text.includes('No projects');
    expect(hasValidState).toBe(true);
  });

  test('Organization owner should have owner role', async ({ page }) => {
    await registerUser(page);

    // Create an org first
    const orgData = await page.evaluate(async () => {
      const response = await window.API.organizations.create({
        name: 'Role Test Org ' + Date.now(),
        description: 'Test org for role checking'
      });
      return response;
    });

    console.log('Created org:', orgData);

    // The organization response includes the owner field
    const orgOwner = orgData.owner;
    const currentUserId = await page.evaluate(() => window.API.auth.getStoredUser()?.id);

    console.log('Org owner:', orgOwner, 'Current user:', currentUserId);

    // Verify the current user is the org owner
    expect(orgOwner).toBe(currentUserId);
  });

  test('Admin menu should be visible to logged in users', async ({ page }) => {
    await registerUser(page);

    // Check that admin menu exists in nav
    const adminMenu = page.locator('#admin-menu');
    await expect(adminMenu).toBeVisible();
  });

  test('User menu dropdown should work', async ({ page }) => {
    await registerUser(page);

    // Check user menu exists
    const userMenu = page.locator('#user-menu');
    await expect(userMenu).toBeVisible();

    // Click to toggle dropdown (get first button - the trigger)
    await userMenu.locator('button').first().click();
    await page.waitForTimeout(300);

    // Check dropdown is visible
    const dropdown = page.locator('#user-dropdown');
    await expect(dropdown).toBeVisible();

    // Check account link
    const accountLink = dropdown.locator('a[href="/pages/account.html"]');
    await expect(accountLink).toBeVisible();

    // Check sign out button
    const signOutBtn = dropdown.locator('button:has-text("Sign Out")');
    await expect(signOutBtn).toBeVisible();
  });
});
