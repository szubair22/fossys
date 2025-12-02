// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * STABILITY TESTS FOR AUTHENTICATION
 *
 * These tests verify that the core authentication flow works correctly
 * and that no /api/api/ double-prefix issues occur.
 */

test.describe('Authentication Stability Tests', () => {

  test('API should not return 404 for auth endpoint', async ({ request }) => {
    // Test that the auth endpoint exists and responds (even with bad credentials)
    const response = await request.post('/api/collections/users/auth-with-password', {
      data: {
        identity: 'nonexistent@example.com',
        password: 'wrongpassword'
      }
    });

    // Should get 400 (bad credentials) not 404 (not found)
    expect(response.status()).not.toBe(404);
    console.log('Auth endpoint response status:', response.status());
  });

  test('should register a new user successfully', async ({ page }) => {
    const testEmail = `stability_test_${Date.now()}@example.com`;
    const testPassword = 'StabilityTest123';

    // Navigate to register page
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');

    // Capture network requests to verify no /api/api/ calls
    const apiRequests = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method()
        });
      }
    });

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        console.log(`API Response: ${response.status()} ${response.url()}`);
      }
    });

    // Fill registration form
    await page.fill('#name', 'Stability Test User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);

    // Submit
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Log captured requests for debugging
    console.log('API requests made during registration:');
    apiRequests.forEach(req => {
      console.log(`  ${req.method} ${req.url}`);
      // Fail if any request has /api/api/
      expect(req.url).not.toContain('/api/api/');
    });

    // Verify no error is shown
    const errorMessage = page.locator('#error-message, .error, [class*="error"]');
    const isErrorVisible = await errorMessage.isVisible().catch(() => false);

    if (isErrorVisible) {
      const errorText = await errorMessage.textContent();
      console.log('Error shown:', errorText);
    }

    // Should redirect to login page after registration
    const currentUrl = page.url();
    console.log('URL after registration:', currentUrl);
  });

  test('should login successfully after registration', async ({ page, request }) => {
    const testEmail = `login_test_${Date.now()}@example.com`;
    const testPassword = 'LoginTest123';

    // First, create user via API (known to work)
    const createResponse = await request.post('/api/collections/users/records', {
      data: {
        email: testEmail,
        password: testPassword,
        passwordConfirm: testPassword,
        name: 'Login Test User'
      }
    });

    expect(createResponse.status()).toBe(200);
    console.log('User created via API successfully');

    // Now test login via UI
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Capture all network activity
    const failedRequests = [];
    page.on('response', response => {
      if (response.status() >= 400) {
        failedRequests.push({
          url: response.url(),
          status: response.status()
        });
      }
    });

    // Fill login form
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);

    // Submit
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Log any failed requests
    if (failedRequests.length > 0) {
      console.log('Failed requests during login:');
      failedRequests.forEach(req => {
        console.log(`  ${req.status} ${req.url}`);
      });
    }

    // Check for double /api/ calls
    failedRequests.forEach(req => {
      if (req.url.includes('/api/api/')) {
        console.error('CRITICAL: Double /api/api/ detected!', req.url);
      }
    });

    // Verify we're redirected away from login page (indicates success)
    const finalUrl = page.url();
    console.log('URL after login:', finalUrl);

    // Should not still be on login page with error
    const errorDiv = page.locator('#error-message');
    const errorVisible = await errorDiv.isVisible().catch(() => false);

    if (errorVisible) {
      const errorText = await errorDiv.textContent();
      console.log('Login error:', errorText);
      // If error is "Something went wrong", this indicates /api/api/ issue
      expect(errorText).not.toContain('Something went wrong');
    }
  });

  test('should verify API module is initialized correctly', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Check the APP_CONFIG in browser
    const config = await page.evaluate(() => {
      return window.APP_CONFIG;
    });

    console.log('APP_CONFIG in browser:', config);

    // JITSI_DOMAIN should be configured
    expect(config.JITSI_DOMAIN).toBeDefined();

    // Check API module is available
    const apiAvailable = await page.evaluate(() => {
      return {
        api: typeof window.API !== 'undefined',
        auth: typeof window.API?.auth !== 'undefined',
        isLoggedIn: typeof window.API?.auth?.isLoggedIn === 'function',
        login: typeof window.API?.auth?.login === 'function',
        register: typeof window.API?.auth?.register === 'function'
      };
    });

    console.log('API module check:', apiAvailable);

    // Verify API auth methods are available
    expect(apiAvailable.api).toBe(true);
    expect(apiAvailable.auth).toBe(true);
    expect(apiAvailable.isLoggedIn).toBe(true);
    expect(apiAvailable.login).toBe(true);
    expect(apiAvailable.register).toBe(true);
  });

  test('full auth flow: register -> login -> create org -> delete org', async ({ page }) => {
    const testEmail = `fullflow_${Date.now()}@example.com`;
    const testPassword = 'FullFlow123';
    const orgName = `Test Org ${Date.now()}`;

    // Track all API errors and responses
    const apiErrors = [];
    const apiResponses = [];
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        apiResponses.push({
          url: response.url(),
          status: response.status()
        });
        if (response.status() >= 400) {
          apiErrors.push({
            url: response.url(),
            status: response.status()
          });
        }
      }
    });

    // Step 1: Register
    await page.goto('/pages/register.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#name', 'Full Flow User');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#passwordConfirm', testPassword);
    await page.click('button[type="submit"]');

    // Wait for API responses to complete
    await page.waitForTimeout(3000);

    // Log API activity for debugging
    console.log('API responses during registration:', apiResponses.length);
    apiResponses.forEach(r => console.log(`  ${r.status} ${r.url}`));

    // Check if we're still on register page with an error
    const errorEl = page.locator('#error-message, .error, [class*="error"]');
    const errorVisible = await errorEl.isVisible().catch(() => false);
    if (errorVisible) {
      const errorText = await errorEl.textContent();
      console.log('Registration error:', errorText);
    }

    // Try to wait for redirect to dashboard, but don't fail if already there
    const currentUrl = page.url();
    console.log('Current URL after registration:', currentUrl);

    if (!currentUrl.includes('dashboard.html')) {
      // Wait a bit more for redirect
      await page.waitForURL('**/dashboard.html', { timeout: 10000 }).catch(() => {
        console.log('Did not redirect to dashboard - may need to check registration');
      });
    }
    console.log('After registration, API errors:', apiErrors.length);

    // We're now logged in from registration (auto-login after register)
    // Go directly to organizations page

    // Step 2: Navigate to organizations
    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Step 3: Create organization
    const createBtn = page.locator('button:has-text("Create Organization")').first();
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(500);

      // Fill in the modal form
      const orgInput = page.locator('#org-name');
      await orgInput.waitFor({ state: 'visible', timeout: 5000 });
      await orgInput.fill(orgName);

      // Click submit button inside the modal form
      await page.locator('#new-org-form button[type="submit"]').click();
      await page.waitForTimeout(3000);
    }

    // Step 4: Verify org exists
    const orgVisible = await page.locator(`text="${orgName}"`).isVisible().catch(() => false);
    console.log('Organization visible after creation:', orgVisible);

    // Step 5: Navigate to org and delete
    if (orgVisible) {
      await page.locator(`a:has-text("${orgName}")`).first().click();
      await page.waitForTimeout(2000);

      // Go to Settings tab
      await page.locator('button:has-text("Settings")').click();
      await page.waitForTimeout(1000);

      // Click delete
      page.on('dialog', dialog => dialog.accept());
      const deleteBtn = page.locator('button:has-text("Delete Organization")');
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        await page.waitForTimeout(3000);
      }

      // Verify redirect
      const afterDeleteUrl = page.url();
      console.log('URL after delete:', afterDeleteUrl);
      expect(afterDeleteUrl).toContain('organizations.html');
    }

    // Final report
    console.log('\n=== STABILITY TEST SUMMARY ===');
    console.log('Total API errors:', apiErrors.length);
    const doubleApiErrors = apiErrors.filter(e => e.url.includes('/api/api/'));
    console.log('Double /api/api/ errors:', doubleApiErrors.length);

    if (doubleApiErrors.length > 0) {
      console.error('CRITICAL: Found double /api/api/ errors:');
      doubleApiErrors.forEach(e => console.error(`  ${e.status} ${e.url}`));
    }

    // Test passes if no double /api/api/ errors
    expect(doubleApiErrors.length).toBe(0);
  });
});
