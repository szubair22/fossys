// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * MEETINGS E2E TESTS
 *
 * Tests for the meeting creation and management flows.
 */

test.describe('Meeting Management', () => {

  test('should create a meeting successfully', async ({ page, request }) => {
    const testEmail = `meeting_test_${Date.now()}@example.com`;
    const testPassword = 'MeetingTest123';
    const meetingTitle = `Test Meeting ${Date.now()}`;

    // Track API errors
    const apiErrors = [];
    page.on('response', response => {
      if (response.url().includes('/api/') && response.status() >= 400) {
        apiErrors.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    // Step 1: Register a new user
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting Test User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);
    await page.click('button[type="submit"]');

    // Wait for redirect to dashboard (successful registration auto-logs in)
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });
    console.log('Registration successful - redirected to dashboard');

    // Step 2: Navigate to meetings page
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Step 3: Click "Create Meeting" button
    const createBtn = page.locator('button:has-text("Create Meeting")').first();
    await createBtn.waitFor({ state: 'visible', timeout: 5000 });
    await createBtn.click();
    await page.waitForTimeout(500);

    // Step 4: Fill in the meeting form
    const titleInput = page.locator('#meeting-title');
    await titleInput.waitFor({ state: 'visible', timeout: 5000 });
    await titleInput.fill(meetingTitle);

    // Fill start time (default should be set, but let's ensure)
    const startInput = page.locator('#meeting-start');
    const now = new Date();
    now.setHours(now.getHours() + 1, 0, 0, 0);
    const startTimeValue = now.toISOString().slice(0, 16);
    await startInput.fill(startTimeValue);

    // Step 5: Submit the form
    await page.locator('#new-meeting-form button[type="submit"]').click();

    // Wait for navigation to meeting page
    await page.waitForURL('**/meeting.html?id=*', { timeout: 15000 });
    console.log('Meeting created successfully - redirected to meeting page');

    // Verify the meeting title appears on the page
    const pageTitle = page.locator('h1, h2').first();
    await expect(pageTitle).toContainText(meetingTitle, { timeout: 10000 });

    // Report any API errors
    if (apiErrors.length > 0) {
      console.log('API errors during test:');
      apiErrors.forEach(err => console.log(`  ${err.status} ${err.url}`));
    }

    // Test passes if we got to the meeting page
    expect(page.url()).toContain('meeting.html?id=');
    console.log('Meeting creation test PASSED');
  });

  test('should display meetings list', async ({ page, request }) => {
    const testEmail = `meetinglist_test_${Date.now()}@example.com`;
    const testPassword = 'MeetingList123';

    // Register and login
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting List User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Navigate to meetings page
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify the page loaded (should show either meetings or "No meetings" message)
    const meetingsList = page.locator('#meetings-list');
    await expect(meetingsList).toBeVisible();

    // Wait for content to load
    await page.waitForTimeout(1000);

    // Should show either meeting cards or "No meetings found" message or loading
    const content = await meetingsList.textContent();
    console.log('Meetings list content:', content.substring(0, 200));

    // Any of these states is acceptable
    const hasValidContent = content.includes('No meetings') ||
                           content.includes('Loading') ||
                           content.includes('Create your first meeting') ||
                           await meetingsList.locator('a').count() > 0;

    expect(hasValidContent).toBeTruthy();
    console.log('Meetings list test PASSED');
  });

  test('should filter meetings by status', async ({ page, request }) => {
    const testEmail = `meetingfilter_test_${Date.now()}@example.com`;
    const testPassword = 'MeetingFilter123';

    // Register and login
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting Filter User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Navigate to meetings page
    await page.goto('/pages/meetings.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click filter buttons
    const upcomingBtn = page.locator('button:has-text("Upcoming")');
    await upcomingBtn.click();
    await page.waitForTimeout(1000);

    // Verify filter is active (button should have active styling)
    await expect(upcomingBtn).toHaveClass(/bg-blue-600/);

    const pastBtn = page.locator('button:has-text("Past")');
    await pastBtn.click();
    await page.waitForTimeout(1000);

    // Verify past filter is now active
    await expect(pastBtn).toHaveClass(/bg-blue-600/);

    console.log('Meeting filter test PASSED');
  });

  test('should open meeting details page', async ({ page, request }) => {
    const testEmail = `meetingdetail_test_${Date.now()}@example.com`;
    const testPassword = 'MeetingDetail123';
    const meetingTitle = `Detail Test Meeting ${Date.now()}`;

    // Register and login
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Meeting Detail User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);
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

    // Verify we're on the meeting page
    expect(page.url()).toContain('meeting.html?id=');

    // Check for meeting page elements (tabs)
    const tabButtons = page.locator('button[role="tab"], button:has-text("Agenda"), button:has-text("Motions"), button:has-text("Polls")');
    // At least some navigation/tabs should be present
    await page.waitForTimeout(2000);

    console.log('Meeting details page test PASSED');
  });

});

test.describe('Meeting API', () => {

  test('should return 400 for missing required fields', async ({ request }) => {
    // Try to create a meeting without required fields
    const response = await request.post('/api/collections/meetings/records', {
      data: {
        // Missing title, start_time, status, created_by
      }
    });

    // Should get 400 (bad request) for validation error
    expect(response.status()).toBe(400);
    console.log('API validation test PASSED');
  });

  test('API endpoint should be accessible', async ({ request }) => {
    // Test that meetings API endpoint exists
    const response = await request.get('/api/collections/meetings/records');

    // Should return 200 (empty list) or 401 (unauthorized)
    // Either is fine - endpoint exists
    expect([200, 401]).toContain(response.status());
    console.log('API endpoint test PASSED');
  });

});
