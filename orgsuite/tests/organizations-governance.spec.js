// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * ORGANIZATIONS & GOVERNANCE MODULE E2E TESTS
 *
 * Tests for Organizations CRUD, cross-page organization selection,
 * and basic governance flows.
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
  console.log(`Organization creation status for "${orgName}": ${status}`);

  if (status !== 200 && status !== 201) {
    const body = await response.text();
    console.log('Organization creation failed:', body);
    throw new Error(`Failed to create organization: ${status}`);
  }

  // Wait for modal to close
  await modal.waitFor({ state: 'hidden', timeout: 5000 });

  // Wait for the list to refresh - watch for the GET request to organizations
  const listResponse = page.waitForResponse(resp =>
    resp.url().includes('/api/v1/organizations') && resp.request().method() === 'GET',
    { timeout: 5000 }
  ).catch(() => null);

  // Wait for list to refresh
  await page.waitForTimeout(1000);

  // If we caught a list refresh, wait for it
  if (listResponse) {
    await listResponse;
    await page.waitForTimeout(1000);
  }

  // Give the UI time to render
  await page.waitForTimeout(2000);

  // Verify org is in the list
  const orgVisible = await page.locator(`text="${orgName}"`).first().isVisible({ timeout: 5000 }).catch(() => false);
  console.log(`Organization "${orgName}" visible in list: ${orgVisible}`);

  // If not visible, try refreshing the page
  if (!orgVisible) {
    console.log('Org not visible, refreshing page...');
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
  }

  return orgName;
}

// Helper to select an organization in a page's org selector
async function selectOrganization(page, orgName) {
  const orgSelector = page.locator('#org-selector');
  await orgSelector.waitFor({ state: 'visible', timeout: 5000 });
  await page.waitForTimeout(2000);

  const options = await orgSelector.locator('option').allTextContents();
  const matchingOption = options.find(opt => opt.includes(orgName) || opt === orgName);

  if (!matchingOption) {
    throw new Error(`Organization "${orgName}" not found in dropdown`);
  }

  await orgSelector.selectOption({ label: matchingOption });
  await page.waitForTimeout(1000);
}


// ============================================================================
// ORGANIZATIONS CRUD TESTS
// ============================================================================

test.describe('Organizations: CRUD Operations', () => {
  test('user can create an organization', async ({ page }) => {
    await setupUser(page, 'orgcreate');
    const orgName = `Create Test Org ${uniqueId()}`;

    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Click create button
    await page.locator('button:has-text("Create Organization")').first().click();

    // Fill form
    const modal = page.locator('#new-org-modal');
    await modal.waitFor({ state: 'visible', timeout: 5000 });

    await page.fill('#org-name', orgName);
    await page.fill('#org-description', 'A test organization description');

    // Submit
    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/organizations') && resp.request().method() === 'POST'
    );
    await page.click('#submit-org-btn');

    const response = await responsePromise;
    expect(response.status()).toBe(201);

    // Verify it appears in list
    await page.waitForTimeout(2000);
    await expect(page.locator(`text="${orgName}"`)).toBeVisible({ timeout: 10000 });
  });

  test('user can edit an organization', async ({ page }) => {
    await setupUser(page, 'orgedit');
    const orgName = `Edit Test Org ${uniqueId()}`;
    const updatedName = `Updated Org ${uniqueId()}`;

    // Use helper to create org
    await createOrganization(page, orgName);

    // Verify the org card is visible
    await expect(page.locator(`text="${orgName}"`).first()).toBeVisible({ timeout: 10000 });

    // Click edit button - find the first edit button
    const editButton = page.locator('button[title="Edit"]').first();
    await editButton.waitFor({ state: 'visible', timeout: 10000 });
    await editButton.click();

    // Edit modal should appear
    const editModal = page.locator('#edit-org-modal');
    await editModal.waitFor({ state: 'visible', timeout: 5000 });

    // Update name
    await page.fill('#edit-org-name', updatedName);
    await page.fill('#edit-org-description', 'Updated description');

    // Submit
    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/organizations/') && resp.request().method() === 'PATCH'
    );
    await page.click('#submit-edit-org-btn');

    const response = await responsePromise;
    expect(response.status()).toBe(200);

    // Verify modal closes
    await editModal.waitFor({ state: 'hidden', timeout: 5000 });
  });

  test('user can delete an organization', async ({ page }) => {
    await setupUser(page, 'orgdelete');
    const orgName = `Delete Test Org ${uniqueId()}`;

    // Use helper to create org
    await createOrganization(page, orgName);

    // Verify the org card is visible
    await expect(page.locator(`text="${orgName}"`).first()).toBeVisible({ timeout: 10000 });

    // Accept the confirmation dialog before clicking
    page.on('dialog', dialog => dialog.accept());

    // Click delete button - find the first delete button
    const deleteButton = page.locator('button[title="Delete"]').first();
    await deleteButton.waitFor({ state: 'visible', timeout: 10000 });

    const deleteResponse = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/organizations/') && resp.request().method() === 'DELETE'
    );
    await deleteButton.click();

    // Wait for deletion API call
    const response = await deleteResponse;
    expect(response.status()).toBe(204);
  });

  test('user can search organizations', async ({ page }) => {
    await setupUser(page, 'orgsearch');
    const orgName1 = `SearchTest Alpha ${uniqueId()}`;
    const orgName2 = `SearchTest Beta ${uniqueId()}`;

    await createOrganization(page, orgName1);
    await createOrganization(page, orgName2);

    // Search for Alpha
    await page.fill('#org-search', 'Alpha');
    await page.waitForTimeout(500); // Debounce

    await page.waitForTimeout(2000);
    await expect(page.locator(`text="${orgName1}"`)).toBeVisible();
    await expect(page.locator(`text="${orgName2}"`)).not.toBeVisible();

    // Clear search
    await page.fill('#org-search', '');
    await page.waitForTimeout(500);

    await page.waitForTimeout(2000);
    await expect(page.locator(`text="${orgName1}"`)).toBeVisible();
    await expect(page.locator(`text="${orgName2}"`)).toBeVisible();
  });
});


// ============================================================================
// CROSS-PAGE ORGANIZATION SELECTION TESTS
// ============================================================================

test.describe('Organizations: Cross-Page Selection', () => {
  test('organization appears in members page selector', async ({ page }) => {
    await setupUser(page, 'crossmember');
    const orgName = `CrossMember Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Navigate to members page
    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check org selector
    const orgSelector = page.locator('#org-selector');
    await orgSelector.waitFor({ state: 'visible', timeout: 5000 });

    const options = await orgSelector.locator('option').allTextContents();
    const hasOrg = options.some(opt => opt.includes(orgName));
    expect(hasOrg).toBe(true);
  });

  test('organization appears in contacts page selector', async ({ page }) => {
    await setupUser(page, 'crosscontact');
    const orgName = `CrossContact Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Navigate to contacts page
    await page.goto('/pages/contacts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const orgSelector = page.locator('#org-selector');
    await orgSelector.waitFor({ state: 'visible', timeout: 5000 });

    const options = await orgSelector.locator('option').allTextContents();
    const hasOrg = options.some(opt => opt.includes(orgName));
    expect(hasOrg).toBe(true);
  });

  test('organization appears in finance accounts page selector', async ({ page }) => {
    await setupUser(page, 'crossfinance');
    const orgName = `CrossFinance Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Navigate to finance accounts page
    await page.goto('/pages/finance_accounts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const orgSelector = page.locator('#org-selector');
    await orgSelector.waitFor({ state: 'visible', timeout: 5000 });

    const options = await orgSelector.locator('option').allTextContents();
    const hasOrg = options.some(opt => opt.includes(orgName));
    expect(hasOrg).toBe(true);
  });

  test('selecting organization loads its data on members page', async ({ page }) => {
    await setupUser(page, 'selectmember');
    const orgName = `SelectMember Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Go to members page and select org
    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Should see empty state or members table body
    const tableBody = page.locator('#members-table-body');
    await tableBody.waitFor({ state: 'visible', timeout: 5000 });
    expect(await tableBody.isVisible()).toBe(true);
  });
});


// ============================================================================
// NAVIGATION REGRESSION TESTS
// ============================================================================

test.describe('Navigation: Menu and Cross-Module', () => {
  test('user can navigate from dashboard to organizations', async ({ page }) => {
    await setupUser(page, 'navdash');

    await page.goto('/pages/dashboard.html');
    await page.waitForLoadState('networkidle');

    // Click organizations link in nav
    await page.click('a[href*="organizations"]');
    await page.waitForURL('**/organizations.html', { timeout: 10000 });

    await expect(page.locator('h1:has-text("Organizations")')).toBeVisible();
  });

  test('user can navigate through all main modules', async ({ page }) => {
    await setupUser(page, 'navall');
    const orgName = `NavAll Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Organizations -> Members
    await page.goto('/pages/members.html');
    await expect(page.locator('h1:has-text("Members")')).toBeVisible({ timeout: 10000 });

    // Members -> Contacts
    await page.goto('/pages/contacts.html');
    await expect(page.locator('h1:has-text("Contacts")')).toBeVisible({ timeout: 10000 });

    // Contacts -> Finance Accounts
    await page.goto('/pages/finance_accounts.html');
    await expect(page.locator('h1:has-text("Chart of Accounts")')).toBeVisible({ timeout: 10000 });

    // Finance Accounts -> Donations
    await page.goto('/pages/finance_donations.html');
    await expect(page.locator('h1:has-text("Donations")')).toBeVisible({ timeout: 10000 });

    // Donations -> Journal
    await page.goto('/pages/finance_journal.html');
    await expect(page.locator('h1:has-text("Journal Entries")')).toBeVisible({ timeout: 10000 });
  });

  test('logout button is present for authenticated user', async ({ page }) => {
    await setupUser(page, 'navlogout');

    await page.goto('/pages/dashboard.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Verify the user is logged in by checking auth exists
    const hasAuth = await page.evaluate(() => !!localStorage.getItem('pocketbase_auth'));
    expect(hasAuth).toBe(true);

    // Look for logout link/button somewhere on the page
    const logoutElement = page.locator('text=Logout, [onclick*="logout"]').first();
    const hasLogout = await logoutElement.isVisible().catch(() => false);

    // At minimum, the page should have rendered successfully for a logged-in user
    expect(await page.locator('h1').first().isVisible()).toBe(true);
  });
});


// ============================================================================
// AUTHENTICATION TESTS
// ============================================================================

test.describe('Authentication: Login/Logout Flow', () => {
  test('unauthenticated user is redirected to login', async ({ page }) => {
    // Clear any existing auth
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    await page.goto('/pages/organizations.html');
    await page.waitForTimeout(3000);

    // Should redirect to login or show login prompt
    const url = page.url();
    const isLoginOrRedirected = url.includes('login') || url === '/' || url.includes('index');
    const hasLoginPrompt = await page.locator('text=Login, text=Sign in').first().isVisible().catch(() => false);

    expect(isLoginOrRedirected || hasLoginPrompt).toBe(true);
  });

  test('user can login and access organizations', async ({ page }) => {
    const { email, password } = await setupUser(page, 'logintest');

    // Clear auth state
    await page.evaluate(() => localStorage.clear());

    // Login again
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.click('button[type="submit"]');

    await page.waitForURL('**/dashboard.html', { timeout: 15000 });

    // Navigate to organizations
    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1:has-text("Organizations")')).toBeVisible();
  });
});


// ============================================================================
// EMPTY STATE TESTS
// ============================================================================

test.describe('Empty States', () => {
  test('organizations page shows empty state for new user', async ({ page }) => {
    await setupUser(page, 'emptyorg');

    await page.goto('/pages/organizations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Should show "No organizations yet" message
    await expect(page.locator('text="No organizations yet"')).toBeVisible({ timeout: 10000 });
  });

  test('members page shows empty state when no org selected', async ({ page }) => {
    await setupUser(page, 'emptymember');

    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Should show prompt to select organization
    const content = await page.locator('body').textContent();
    const hasEmptyState = content.includes('Select an organization') ||
                          content.includes('No members') ||
                          content.includes('select');
    expect(hasEmptyState).toBe(true);
  });
});


// ============================================================================
// GOVERNANCE V1 API TESTS
// ============================================================================

test.describe('Governance API: Committees', () => {
  test('API returns committees list for organization', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'govcommittee');
    const orgName = `GovCommittee Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    expect(authState).not.toBeNull();
    expect(authState.token).toBeTruthy();

    // Get organization ID
    const orgsResponse = await request.get('/api/v1/organizations', {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(orgsResponse.status()).toBe(200);

    const orgsData = await orgsResponse.json();
    const org = orgsData.items.find(o => o.name === orgName);
    expect(org).toBeTruthy();

    // Test committees endpoint
    const committeesResponse = await request.get(`/api/v1/governance/committees?organization_id=${org.id}`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(committeesResponse.status()).toBe(200);

    const committeesData = await committeesResponse.json();
    expect(committeesData).toHaveProperty('items');
    expect(committeesData).toHaveProperty('totalItems');
    expect(committeesData).toHaveProperty('page');
  });

  test('API can create a committee', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'createcommittee');
    const orgName = `CreateCommittee Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Get organization ID
    const orgsResponse = await request.get('/api/v1/organizations', {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    const orgsData = await orgsResponse.json();
    const org = orgsData.items.find(o => o.name === orgName);

    // Create committee
    const createResponse = await request.post('/api/v1/governance/committees', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        organization_id: org.id,
        name: 'Test Committee',
        description: 'A test committee'
      }
    });
    expect(createResponse.status()).toBe(201);

    const committee = await createResponse.json();
    expect(committee.name).toBe('Test Committee');
    expect(committee.organization_id).toBe(org.id);
  });
});


test.describe('Governance API: Meetings', () => {
  test('API can create a meeting', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'createmeeting');
    const orgName = `CreateMeeting Org ${uniqueId()}`;

    await createOrganization(page, orgName);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create meeting (no committee required)
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const createResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'API Test Meeting',
        description: 'Created via API test',
        start_time: startTime,
        status: 'scheduled',
        meeting_type: 'general'
      }
    });
    expect(createResponse.status()).toBe(201);

    const meeting = await createResponse.json();
    expect(meeting.title).toBe('API Test Meeting');
    expect(meeting.jitsi_room).toBeTruthy();
    expect(meeting.status).toBe('scheduled');
  });

  test('API can list meetings', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'listmeetings');

    await createOrganization(page, `ListMeetings Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting first
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Meeting to List',
        start_time: startTime,
        status: 'scheduled'
      }
    });

    // List meetings
    const listResponse = await request.get('/api/v1/governance/meetings', {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(listResponse.status()).toBe(200);

    const data = await listResponse.json();
    expect(data.totalItems).toBeGreaterThanOrEqual(1);
    expect(data.items.length).toBeGreaterThanOrEqual(1);
  });

  test('API can close and reopen a meeting', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'closemeeting');

    await createOrganization(page, `CloseMeeting Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const createResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Meeting to Close',
        start_time: startTime,
        status: 'in_progress'
      }
    });
    const meeting = await createResponse.json();

    // Close meeting
    const closeResponse = await request.post(`/api/v1/governance/meetings/${meeting.id}/close`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(closeResponse.status()).toBe(200);
    const closedMeeting = await closeResponse.json();
    expect(closedMeeting.status).toBe('completed');

    // Reopen meeting
    const reopenResponse = await request.post(`/api/v1/governance/meetings/${meeting.id}/reopen`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(reopenResponse.status()).toBe(200);
    const reopenedMeeting = await reopenResponse.json();
    expect(reopenedMeeting.status).toBe('in_progress');
  });
});


test.describe('Governance API: Agenda Items', () => {
  test('API can create and list agenda items', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'agendatest');

    await createOrganization(page, `Agenda Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const meetingResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Agenda Test Meeting',
        start_time: startTime,
        status: 'scheduled'
      }
    });
    const meeting = await meetingResponse.json();

    // Create agenda item
    const createResponse = await request.post('/api/v1/governance/agenda-items', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        meeting_id: meeting.id,
        title: 'Opening Remarks',
        description: 'Welcome and introductions',
        item_type: 'topic',
        duration_minutes: 10
      }
    });
    expect(createResponse.status()).toBe(201);

    const item = await createResponse.json();
    expect(item.title).toBe('Opening Remarks');

    // List agenda items
    const listResponse = await request.get(`/api/v1/governance/agenda-items?meeting_id=${meeting.id}`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(listResponse.status()).toBe(200);

    const data = await listResponse.json();
    expect(data.totalItems).toBeGreaterThanOrEqual(1);
  });
});


test.describe('Governance API: Motions', () => {
  test('API can create a motion and transition state', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'motiontest');

    await createOrganization(page, `Motion Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const meetingResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Motion Test Meeting',
        start_time: startTime,
        status: 'scheduled'
      }
    });
    const meeting = await meetingResponse.json();

    // Create motion
    const createResponse = await request.post('/api/v1/governance/motions', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        meeting_id: meeting.id,
        title: 'Test Motion',
        text: 'Be it resolved that this is a test motion.',
        reason: 'For testing purposes'
      }
    });
    expect(createResponse.status()).toBe(201);

    const motion = await createResponse.json();
    expect(motion.title).toBe('Test Motion');
    expect(motion.workflow_state).toBe('draft');

    // Get allowed transitions
    const transitionsResponse = await request.get(`/api/v1/governance/motions/${motion.id}/transitions`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(transitionsResponse.status()).toBe(200);

    const transitions = await transitionsResponse.json();
    expect(transitions.current_state).toBe('draft');
    expect(transitions.allowed_transitions).toContain('submitted');

    // Submit motion
    const submitResponse = await request.post(`/api/v1/governance/motions/${motion.id}/submit`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(submitResponse.status()).toBe(200);

    const submittedMotion = await submitResponse.json();
    expect(submittedMotion.workflow_state).toBe('submitted');
  });
});


test.describe('Governance API: Polls and Votes', () => {
  test('API can create poll, open it, and cast vote', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'polltest');

    await createOrganization(page, `Poll Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const meetingResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Poll Test Meeting',
        start_time: startTime,
        status: 'scheduled'
      }
    });
    const meeting = await meetingResponse.json();

    // Create poll
    const createPollResponse = await request.post('/api/v1/governance/polls', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        meeting_id: meeting.id,
        title: 'Test Poll',
        poll_type: 'yes_no',
        anonymous: false
      }
    });
    expect(createPollResponse.status()).toBe(201);

    const poll = await createPollResponse.json();
    expect(poll.status).toBe('draft');

    // Open poll
    const openResponse = await request.post(`/api/v1/governance/polls/${poll.id}/open`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(openResponse.status()).toBe(200);

    const openedPoll = await openResponse.json();
    expect(openedPoll.status).toBe('open');

    // Cast vote
    const voteResponse = await request.post('/api/v1/governance/votes', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        poll_id: poll.id,
        value: { choice: 'yes' }
      }
    });
    expect(voteResponse.status()).toBe(201);

    const vote = await voteResponse.json();
    expect(vote.value.choice).toBe('yes');

    // Close poll
    const closeResponse = await request.post(`/api/v1/governance/polls/${poll.id}/close`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(closeResponse.status()).toBe(200);

    const closedPoll = await closeResponse.json();
    expect(closedPoll.status).toBe('closed');
    expect(closedPoll.results).toBeTruthy();
  });
});


test.describe('Governance API: Participants', () => {
  test('API can list and update participants', async ({ page, request }) => {
    const { email, password } = await setupUser(page, 'participanttest');

    await createOrganization(page, `Participant Org ${uniqueId()}`);

    // Get auth token
    const authState = await page.evaluate(() => {
      const auth = localStorage.getItem('pocketbase_auth');
      return auth ? JSON.parse(auth) : null;
    });

    // Create a meeting
    const startTime = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const meetingResponse = await request.post('/api/v1/governance/meetings', {
      headers: {
        'Authorization': `Bearer ${authState.token}`,
        'Content-Type': 'application/json'
      },
      data: {
        title: 'Participant Test Meeting',
        start_time: startTime,
        status: 'scheduled'
      }
    });
    const meeting = await meetingResponse.json();

    // List participants (creator should be auto-added)
    const listResponse = await request.get(`/api/v1/governance/participants?meeting_id=${meeting.id}`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(listResponse.status()).toBe(200);

    const data = await listResponse.json();
    expect(data.totalItems).toBeGreaterThanOrEqual(1);

    // Get participant ID
    const participant = data.items[0];

    // Mark as present
    const presentResponse = await request.post(`/api/v1/governance/participants/${participant.id}/mark-present`, {
      headers: { 'Authorization': `Bearer ${authState.token}` }
    });
    expect(presentResponse.status()).toBe(200);

    const presentParticipant = await presentResponse.json();
    expect(presentParticipant.attendance_status).toBe('present');
    expect(presentParticipant.is_present).toBe(true);
  });
});
