// Playwright tests for Documents module v1
const { test, expect } = require('@playwright/test');

// Helpers: register users, create org, assign roles, select org
async function registerUser(page, prefix = 'doc') {
  const email = `${prefix}_${Date.now()}@example.com`;
  const password = 'DocTest123';
  // Use API to register + auto-login to avoid flaky UI selectors
  await page.goto('/pages/login.html');
  await page.waitForLoadState('networkidle');
  await page.evaluate(async ({ prefix, email, password }) => {
    const name = `Docs ${prefix} User`;
    await window.API.auth.register(name, email, password, password);
  }, { prefix, email, password });
  // Ensure we have a user and token
  const userExists = await page.evaluate(() => !!window.API.auth.getStoredUser());
  expect(userExists).toBeTruthy();
  return { email, password };
}

async function createOrg(page, name = 'Docs Test Org') {
  const org = await page.evaluate(async (orgName) => {
    const created = await window.API.organizations.create({ name: `${orgName} ${Date.now()}` });
    window.API.org.setCurrentId(created.id);
    return created;
  }, name);
  return org;
}

async function addMemberByEmail(page, orgId, email, role) {
  // Uses FastAPI v1 governance org-invite style helper
  await page.evaluate(async ({ orgId, email, role }) => {
    await window.API.governance.orgMemberships.addByEmail(orgId, { email, role });
    // Clear role cache to ensure UI updates
    window.API.roles.clearCache();
  }, { orgId, email, role });
}

async function loginAsViewerAndSelectOrg(page) {
  // Owner creates org, invites second user as viewer; then log in as viewer
  const owner = await registerUser(page, 'owner');
  const org = await createOrg(page);
  await page.context().storageState();
  // Create viewer account (new context within same page)
  const viewer = await registerUser(page, 'viewer');
  // Ensure org exists and assign viewer role in that org (switch back to owner session via login)
  await page.evaluate(async (credentials) => {
    await window.API.auth.logout();
    await window.API.auth.login(credentials.email, credentials.password);
  }, owner);
  await addMemberByEmail(page, org.id, viewer.email, 'viewer');
  // Switch to viewer session and select org
  await page.evaluate(async (credentials) => {
    await window.API.auth.logout();
    await window.API.auth.login(credentials.email, credentials.password);
  }, viewer);
  await page.evaluate((orgId) => {
    window.API.org.setCurrentId(orgId);
    window.API.roles.clearCache();
  }, org.id);
}

async function loginAsMemberAndSelectOrg(page) {
  const owner = await registerUser(page, 'owner2');
  const org = await createOrg(page, 'Docs Test Org 2');
  const member = await registerUser(page, 'member');
  // Back to owner to assign role
  await page.evaluate(async (credentials) => {
    await window.API.auth.logout();
    await window.API.auth.login(credentials.email, credentials.password);
  }, owner);
  await addMemberByEmail(page, org.id, member.email, 'member');
  // Switch to member
  await page.evaluate(async (credentials) => {
    await window.API.auth.logout();
    await window.API.auth.login(credentials.email, credentials.password);
  }, member);
  await page.evaluate((orgId) => {
    window.API.org.setCurrentId(orgId);
    window.API.roles.clearCache();
  }, org.id);
}

test.describe('Documents Module', () => {
  // Existing structural smoke tests
  test('viewer sees Documents page elements', async ({ page }) => {
    await page.goto('/pages/documents.html');
    await expect(page.locator('h1')).toContainText('Documents');
    await expect(page.locator('#folderTree')).toHaveCount(1);
    await expect(page.locator('#filesTable')).toHaveCount(1);
  });

  test('Documents actions controls exist', async ({ page }) => {
    await page.goto('/pages/documents.html');
    // Buttons exist in DOM; visibility may depend on role
    await expect(page.locator('#newFolderBtn')).toHaveCount(1);
    await expect(page.locator('#uploadBtn')).toHaveCount(1);
  });
});

test.describe('Documents Module - Roles', () => {
  test('viewer cannot upload or create folder', async ({ page }) => {
    await loginAsViewerAndSelectOrg(page);
    await page.goto('/pages/documents.html');
    await page.waitForLoadState('networkidle');
    // Allow async role check to complete
    await page.waitForTimeout(300);

    await expect(page.locator('h1')).toContainText('Documents');
    // folderTree exists (may be empty, so check count not visibility)
    await expect(page.locator('#folderTree')).toHaveCount(1);

    // Role-based visibility: viewer should not see action controls
    await expect(page.locator('#uploadBtn')).toBeHidden();
    await expect(page.locator('#newFolderBtn')).toBeHidden();
  });

  test('member/admin can see upload and new folder controls', async ({ page }) => {
    await loginAsMemberAndSelectOrg(page);
    await page.goto('/pages/documents.html');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1')).toContainText('Documents');
    // folderTree exists (may be empty, so check count not visibility)
    await expect(page.locator('#folderTree')).toHaveCount(1);

    // Role-based visibility: member should see action controls
    await expect(page.locator('#uploadBtn')).toBeVisible();
    await expect(page.locator('#newFolderBtn')).toBeVisible();
  });
});
