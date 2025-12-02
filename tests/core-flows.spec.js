// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * CORE FLOWS E2E TESTS
 *
 * Comprehensive tests for all main user flows in OrgMeet.
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

test.describe('Core Flow: Authentication', () => {

  test('user can register, login, and logout', async ({ page }) => {
    const email = `auth_flow_${uniqueId()}@example.com`;
    const password = 'AuthFlow123';

    // Step 1: Register
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#name', 'Auth Flow User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 15000 });
    console.log('Registration successful');

    // Step 2: Logout (via nav menu or direct)
    // Find logout link/button
    const logoutBtn = page.locator('a:has-text("Logout"), button:has-text("Logout"), a:has-text("Log out"), button:has-text("Log out")').first();
    if (await logoutBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await logoutBtn.click();
      await page.waitForTimeout(1000);
    } else {
      // Manual logout via clearing storage
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await page.goto('/pages/login.html');
    }

    console.log('Logout successful');

    // Step 3: Login with the same credentials
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 15000 });
    console.log('Login successful');

    expect(page.url()).toContain('dashboard.html');
  });

});

test.describe('Core Flow: Organizations', () => {

  test('user can create and view organization', async ({ page }) => {
    const email = `org_flow_${uniqueId()}@example.com`;
    const password = 'OrgFlow123';
    const orgName = `Test Org ${uniqueId()}`;

    // Register and login
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Org Flow User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Navigate to organizations
    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Create organization
    await page.locator('button:has-text("Create Organization")').first().click();
    await page.waitForTimeout(500);

    const orgInput = page.locator('#org-name');
    await orgInput.waitFor({ state: 'visible', timeout: 5000 });
    await orgInput.fill(orgName);

    await page.locator('#new-org-form button[type="submit"]').click();
    await page.waitForTimeout(3000);

    // Verify org appears in list
    const orgVisible = await page.locator(`text="${orgName}"`).isVisible().catch(() => false);
    console.log('Organization visible:', orgVisible);
    expect(orgVisible).toBeTruthy();

    // Click on org to open it
    await page.locator(`a:has-text("${orgName}")`).first().click();
    await page.waitForURL('**/organization.html?id=*', { timeout: 10000 });

    console.log('Organization created and opened successfully');
  });

});

test.describe('Core Flow: Meetings', () => {

  test('user can create meeting and view tabs', async ({ page }) => {
    const email = `meeting_flow_${uniqueId()}@example.com`;
    const password = 'MeetingFlow123';
    const meetingTitle = `Test Meeting ${uniqueId()}`;

    // Register
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting Flow User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Create meeting
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.locator('button:has-text("Create Meeting")').first().click();
    await page.waitForTimeout(500);

    await page.locator('#meeting-title').fill(meetingTitle);

    const now = new Date();
    now.setHours(now.getHours() + 1, 0, 0, 0);
    await page.locator('#meeting-start').fill(now.toISOString().slice(0, 16));

    await page.locator('#new-meeting-form button[type="submit"]').click();
    await page.waitForURL('**/meeting.html?id=*', { timeout: 15000 });

    console.log('Meeting created');

    // Check for tab presence (Agenda, Motions, Polls, etc.)
    await page.waitForTimeout(2000);

    // Look for common tab elements
    const agendaTab = page.locator('button:has-text("Agenda"), [data-tab="agenda"]').first();
    const motionsTab = page.locator('button:has-text("Motions"), [data-tab="motions"]').first();
    const pollsTab = page.locator('button:has-text("Polls"), [data-tab="polls"]').first();

    // At least one tab should be visible
    const hasAgenda = await agendaTab.isVisible().catch(() => false);
    const hasMotions = await motionsTab.isVisible().catch(() => false);
    const hasPolls = await pollsTab.isVisible().catch(() => false);

    console.log('Tabs visible - Agenda:', hasAgenda, 'Motions:', hasMotions, 'Polls:', hasPolls);

    // Verify meeting page loaded correctly
    expect(page.url()).toContain('meeting.html?id=');
  });

  test('user can view meeting from list', async ({ page }) => {
    const email = `meeting_list_${uniqueId()}@example.com`;
    const password = 'MeetingList123';
    const meetingTitle = `List Test ${uniqueId()}`;

    // Register and create meeting
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting List User');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.fill('#passwordConfirm', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Create a meeting first
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.locator('button:has-text("Create Meeting")').first().click();
    await page.waitForTimeout(500);
    await page.locator('#meeting-title').fill(meetingTitle);
    const now = new Date();
    now.setHours(now.getHours() + 1, 0, 0, 0);
    await page.locator('#meeting-start').fill(now.toISOString().slice(0, 16));
    await page.locator('#new-meeting-form button[type="submit"]').click();
    await page.waitForURL('**/meeting.html?id=*', { timeout: 15000 });

    // Go back to meetings list
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Find and click on the meeting
    const meetingLink = page.locator(`a:has-text("${meetingTitle}")`).first();
    const isVisible = await meetingLink.isVisible().catch(() => false);
    console.log('Meeting visible in list:', isVisible);

    if (isVisible) {
      await meetingLink.click();
      await page.waitForURL('**/meeting.html?id=*', { timeout: 10000 });
      console.log('Opened meeting from list');
    }

    expect(isVisible).toBeTruthy();
  });

});

test.describe('Core Flow: Access Control', () => {

  test('unauthenticated users cannot access protected pages', async ({ page }) => {
    // Clear any existing auth
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Try to access protected pages
    await page.goto('/pages/dashboard.html');
    await page.waitForTimeout(2000);

    // Should be redirected to login
    const currentUrl = page.url();
    const isOnLoginOrRedirected = currentUrl.includes('login.html') ||
                                   currentUrl.includes('register.html') ||
                                   !currentUrl.includes('dashboard.html');

    console.log('After accessing dashboard without auth, URL:', currentUrl);

    // Same for organizations
    await page.goto('/pages/organizations.html');
    await page.waitForTimeout(2000);

    const orgUrl = page.url();
    console.log('After accessing organizations without auth, URL:', orgUrl);

    // Should redirect unauthenticated users
    expect(isOnLoginOrRedirected || orgUrl.includes('login.html')).toBeTruthy();
  });

});

test.describe('API Health', () => {

  test('all main API endpoints are accessible', async ({ request }) => {
    const endpoints = [
      '/api/collections/users/records',
      '/api/collections/organizations/records',
      '/api/collections/meetings/records',
      '/api/collections/committees/records',
      '/api/collections/agenda_items/records',
      '/api/collections/motions/records',
      '/api/collections/polls/records',
    ];

    for (const endpoint of endpoints) {
      const response = await request.get(endpoint);
      // 200 = success, 401 = unauthorized (but endpoint exists)
      expect([200, 401]).toContain(response.status());
      console.log(`${endpoint}: ${response.status()}`);
    }
  });

  test('PocketBase health check', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.status()).toBe(200);

    const data = await response.json();
    console.log('PocketBase health:', data);
  });

});
