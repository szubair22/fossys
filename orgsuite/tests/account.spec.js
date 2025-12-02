// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * ACCOUNT MANAGEMENT E2E TESTS
 *
 * Tests for user profile viewing/editing and password change flows.
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

// Helper to register and login a user
async function registerAndLogin(page, email, password, name = 'Test User') {
  await page.goto('/pages/register.html');
  await page.waitForLoadState('networkidle');
  await page.fill('#name', name);
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.fill('#passwordConfirm', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard.html', { timeout: 15000 });
  await page.waitForTimeout(1000);
}

// Helper to navigate to account page using the nav menu (preserves auth)
async function goToAccountPage(page) {
  // Open user dropdown menu
  await page.locator('#user-menu button').first().click();
  await page.waitForTimeout(500);

  // Click "My Account" link
  const accountLink = page.locator('a:has-text("My Account")');
  await accountLink.waitFor({ state: 'visible', timeout: 5000 });
  await accountLink.click();

  await page.waitForURL('**/account.html', { timeout: 10000 });
  await page.waitForTimeout(1000);

  // Wait for profile form to be loaded
  await page.locator('#profile-form').waitFor({ state: 'visible', timeout: 10000 });
}

test.describe('Account: View Profile Page', () => {

  test('user can access account page from navigation', async ({ page }) => {
    const email = `account_nav_${uniqueId()}@example.com`;
    const password = 'AccountNav123';

    await registerAndLogin(page, email, password, 'Account Nav User');

    // Open user dropdown menu
    await page.locator('#user-menu button').first().click();
    await page.waitForTimeout(500);

    // Click "My Account" link
    const accountLink = page.locator('a:has-text("My Account")');
    await accountLink.waitFor({ state: 'visible', timeout: 5000 });
    await accountLink.click();

    await page.waitForURL('**/account.html', { timeout: 10000 });
    expect(page.url()).toContain('account.html');

    console.log('Successfully navigated to account page');
  });

  test('account page displays user information', async ({ page }) => {
    const email = `account_display_${uniqueId()}@example.com`;
    const password = 'AccountDisplay123';
    const userName = 'Display Test User';

    await registerAndLogin(page, email, password, userName);
    await goToAccountPage(page);

    // Check email is displayed
    const emailField = page.locator('#email');
    await emailField.waitFor({ state: 'visible', timeout: 5000 });
    await expect(emailField).toHaveValue(email);

    // Check name is displayed
    const nameField = page.locator('#name');
    await expect(nameField).toHaveValue(userName);

    // Check account ID is shown
    const accountId = page.locator('#account-id');
    const idText = await accountId.textContent();
    expect(idText).not.toBe('-');
    expect(idText.length).toBeGreaterThan(5);

    // Check member since date is shown
    const memberSince = page.locator('#member-since');
    const dateText = await memberSince.textContent();
    expect(dateText).not.toBe('-');

    console.log('Account page displays user info correctly');
  });

});

test.describe('Account: Update Profile', () => {

  test('user can update display name', async ({ page }) => {
    const email = `profile_update_${uniqueId()}@example.com`;
    const password = 'ProfileUpdate123';
    const newDisplayName = 'Updated Display Name';

    await registerAndLogin(page, email, password, 'Original Name');
    await goToAccountPage(page);

    // Update display name
    const displayNameInput = page.locator('#display_name');
    await displayNameInput.waitFor({ state: 'visible', timeout: 5000 });
    await displayNameInput.fill(newDisplayName);

    // Submit profile form
    await page.locator('#profile-form button[type="submit"]').click();
    await page.waitForTimeout(2000);

    // Check for success notification
    const notification = page.locator('.notification:has-text("Profile updated")');
    await expect(notification).toBeVisible({ timeout: 5000 });

    console.log('Display name updated successfully');
  });

  test('user can update timezone', async ({ page }) => {
    const email = `timezone_update_${uniqueId()}@example.com`;
    const password = 'TimezoneUpdate123';

    await registerAndLogin(page, email, password, 'Timezone User');
    await goToAccountPage(page);

    // Select timezone
    const timezoneSelect = page.locator('#timezone');
    await timezoneSelect.waitFor({ state: 'visible', timeout: 5000 });
    await timezoneSelect.selectOption('America/Chicago');

    // Submit form
    await page.locator('#profile-form button[type="submit"]').click();
    await page.waitForTimeout(2000);

    // Refresh page and verify
    await page.reload();
    await page.waitForTimeout(2000);

    const selectedTimezone = await page.locator('#timezone').inputValue();
    expect(selectedTimezone).toBe('America/Chicago');

    console.log('Timezone updated and persisted');
  });

});

test.describe('Account: Notification Preferences', () => {

  test('user can toggle notification preferences', async ({ page }) => {
    const email = `notif_prefs_${uniqueId()}@example.com`;
    const password = 'NotifPrefs123';

    await registerAndLogin(page, email, password, 'Notification User');
    await goToAccountPage(page);

    // Toggle off meeting invites
    const invitesCheckbox = page.locator('#notify_meeting_invites');
    await invitesCheckbox.waitFor({ state: 'visible', timeout: 5000 });
    const wasChecked = await invitesCheckbox.isChecked();
    await invitesCheckbox.click();
    await page.waitForTimeout(500);

    // Submit notifications form
    await page.locator('#notifications-form button[type="submit"]').click();
    await page.waitForTimeout(2000);

    // Check for success notification
    const notification = page.locator('.notification:has-text("preferences saved")');
    await expect(notification).toBeVisible({ timeout: 5000 });

    // Refresh and verify
    await page.reload();
    await page.waitForTimeout(2000);

    const nowChecked = await page.locator('#notify_meeting_invites').isChecked();
    expect(nowChecked).toBe(!wasChecked);

    console.log('Notification preferences toggled and saved');
  });

});

test.describe('Account: Change Password', () => {

  test('user can change password with valid credentials', async ({ page }) => {
    const email = `password_change_${uniqueId()}@example.com`;
    const oldPassword = 'OldPassword123';
    const newPassword = 'NewPassword456';

    await registerAndLogin(page, email, oldPassword, 'Password Change User');
    await goToAccountPage(page);

    // Fill in password change form
    const currentPasswordInput = page.locator('#current_password');
    await currentPasswordInput.waitFor({ state: 'visible', timeout: 5000 });
    await currentPasswordInput.fill(oldPassword);
    await page.locator('#new_password').fill(newPassword);
    await page.locator('#confirm_password').fill(newPassword);

    // Submit password form
    await page.locator('#password-form button[type="submit"]').click();
    await page.waitForTimeout(3000);

    // Check for success notification
    const notification = page.locator('.notification:has-text("Password changed")');
    await expect(notification).toBeVisible({ timeout: 5000 });

    console.log('Password changed successfully');

    // Logout and login with new password
    await page.goto('/pages/login.html');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload();
    await page.waitForLoadState('networkidle');

    await page.fill('#email', email);
    await page.fill('#password', newPassword);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 15000 });
    console.log('Login with new password successful');
  });

  test('password change fails with wrong current password', async ({ page }) => {
    const email = `password_fail_${uniqueId()}@example.com`;
    const password = 'CorrectPassword123';

    await registerAndLogin(page, email, password, 'Password Fail User');
    await goToAccountPage(page);

    // Fill in with wrong current password
    const currentPasswordInput = page.locator('#current_password');
    await currentPasswordInput.waitFor({ state: 'visible', timeout: 5000 });
    await currentPasswordInput.fill('WrongPassword');
    await page.locator('#new_password').fill('NewPassword456');
    await page.locator('#confirm_password').fill('NewPassword456');

    // Submit
    await page.locator('#password-form button[type="submit"]').click();
    await page.waitForTimeout(3000);

    // Check for error notification
    const notification = page.locator('.notification.bg-red-500, .notification:has-text("incorrect")');
    await expect(notification).toBeVisible({ timeout: 5000 });

    console.log('Password change correctly failed with wrong current password');
  });

  test('password change shows error when passwords do not match', async ({ page }) => {
    const email = `password_mismatch_${uniqueId()}@example.com`;
    const password = 'CorrectPassword123';

    await registerAndLogin(page, email, password, 'Mismatch User');
    await goToAccountPage(page);

    // Fill in mismatched passwords
    const currentPasswordInput = page.locator('#current_password');
    await currentPasswordInput.waitFor({ state: 'visible', timeout: 5000 });
    await currentPasswordInput.fill(password);
    await page.locator('#new_password').fill('NewPassword456');
    await page.locator('#confirm_password').fill('DifferentPassword789');

    // Submit
    await page.locator('#password-form button[type="submit"]').click();
    await page.waitForTimeout(1000);

    // Check for error message
    const errorDiv = page.locator('#password-error');
    await expect(errorDiv).toBeVisible();
    await expect(errorDiv).toContainText('do not match');

    console.log('Password mismatch error shown correctly');
  });

});

test.describe('Account: Sign Out', () => {

  test('user can sign out from account page', async ({ page }) => {
    const email = `signout_${uniqueId()}@example.com`;
    const password = 'SignOut123';

    await registerAndLogin(page, email, password, 'Sign Out User');
    await goToAccountPage(page);

    // Click sign out button
    const signOutBtn = page.locator('button:has-text("Sign Out")');
    await signOutBtn.waitFor({ state: 'visible', timeout: 5000 });
    await signOutBtn.click();
    await page.waitForTimeout(2000);

    // Should be redirected to home or login
    const currentUrl = page.url();
    console.log('After sign out, URL:', currentUrl);
    expect(currentUrl).not.toContain('account.html');
  });

});
