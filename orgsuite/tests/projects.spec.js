// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PROJECTS MODULE TESTS
 *
 * Tests for the Projects feature including:
 * - API endpoint availability
 * - UI structure and navigation
 * - Role-based access controls
 */

test.describe('Projects Module Tests', () => {

  // Helper to register and login a test user
  async function loginTestUser(page) {
    const email = `projects_test_${Date.now()}@example.com`;
    const password = 'ProjectTest123';

    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#name', 'Project Test User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 10000 });
    return { email, password };
  }

  test('Projects API endpoint should be accessible', async ({ request }) => {
    // Test projects list endpoint - should require auth
    const response = await request.get('/api/v1/events/projects?organization_id=test');
    // Should get 401 Unauthorized without auth
    expect(response.status()).toBe(401);
  });

  test('Projects page should load with proper structure when logged in', async ({ page }) => {
    await loginTestUser(page);

    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    // Check page title
    const title = await page.title();
    expect(title).toContain('Projects');

    // Check org selector exists
    const orgSelector = page.locator('#org-selector');
    await expect(orgSelector).toBeVisible();

    // Check stats cards exist
    await expect(page.locator('#stat-total')).toBeVisible();
    await expect(page.locator('#stat-active')).toBeVisible();
    await expect(page.locator('#stat-planned')).toBeVisible();
    await expect(page.locator('#stat-completed')).toBeVisible();

    // Check projects table exists
    await expect(page.locator('#projects-list')).toBeVisible();
  });

  test('Projects API module should be available in browser', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const apiCheck = await page.evaluate(() => {
      return {
        eventsExists: typeof window.API?.events !== 'undefined',
        projectsExists: typeof window.API?.events?.projects !== 'undefined',
        listExists: typeof window.API?.events?.projects?.list === 'function',
        createExists: typeof window.API?.events?.projects?.create === 'function',
        updateExists: typeof window.API?.events?.projects?.update === 'function',
        deleteExists: typeof window.API?.events?.projects?.delete === 'function'
      };
    });

    console.log('API events.projects methods:', apiCheck);
    expect(apiCheck.eventsExists).toBe(true);
    expect(apiCheck.projectsExists).toBe(true);
    expect(apiCheck.listExists).toBe(true);
    expect(apiCheck.createExists).toBe(true);
    expect(apiCheck.updateExists).toBe(true);
    expect(apiCheck.deleteExists).toBe(true);
  });

  test('Projects page should have add project modal when logged in', async ({ page }) => {
    await loginTestUser(page);

    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    // Check modal exists
    const modal = page.locator('#project-modal');
    await expect(modal).toBeHidden();

    // Check modal form elements exist
    const pageContent = await page.content();
    expect(pageContent).toContain('project-name');
    expect(pageContent).toContain('project-description');
    expect(pageContent).toContain('project-status');
    expect(pageContent).toContain('project-start-date');
    expect(pageContent).toContain('project-end-date');
  });

  test('Projects page should have delete confirmation modal when logged in', async ({ page }) => {
    await loginTestUser(page);

    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    // Check delete modal exists
    const deleteModal = page.locator('#delete-modal');
    await expect(deleteModal).toBeHidden();

    // Check delete confirmation elements
    const pageContent = await page.content();
    expect(pageContent).toContain('delete-project-name');
    expect(pageContent).toContain('confirmDelete');
  });

  test('Navigation should include Projects under Governance', async ({ page }) => {
    await loginTestUser(page);

    // Check navigation structure
    const nav = page.locator('#nav-menu');

    // Find the Governance button (first match - the dropdown trigger)
    const governanceBtn = nav.locator('button:has-text("Governance")').first();
    await expect(governanceBtn).toBeVisible();

    // Hover to see dropdown
    await governanceBtn.hover();
    await page.waitForTimeout(500);

    // Check Projects link exists
    const projectsLink = page.locator('a[href="/pages/projects.html"]');
    await expect(projectsLink).toBeVisible();
  });

  test('Add project button should be hidden by default until org is selected', async ({ page }) => {
    // Create a user and login
    const email = `projects_btn_${Date.now()}@example.com`;
    const password = 'TestBtn123';

    // Register user
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#name', 'Btn Test User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 10000 });

    // Navigate to projects page
    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    // Add button should be hidden (no org selected yet)
    const addBtn = page.locator('#add-project-btn');
    await expect(addBtn).toBeHidden();
  });

  test('Status filter should have all status options', async ({ page }) => {
    await loginTestUser(page);

    await page.goto('/pages/projects.html');
    await page.waitForLoadState('networkidle');

    const statusFilter = page.locator('#status-filter');
    await expect(statusFilter).toBeVisible();

    // Check all status options
    const options = await statusFilter.locator('option').allTextContents();
    expect(options).toContain('All Statuses');
    expect(options).toContain('Planned');
    expect(options).toContain('Active');
    expect(options).toContain('On Hold');
    expect(options).toContain('Completed');
    expect(options).toContain('Cancelled');
  });
});
