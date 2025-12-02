// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * MEMBERSHIP & FINANCE MODULES E2E TESTS
 *
 * Tests for Members, Contacts, Accounts, Journal Entries, and Donations.
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

// Helper to login or register a user and return to dashboard
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

// Helper to create an organization and return its ID
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

  // Listen for the v1 API request to complete
  const responsePromise = page.waitForResponse(resp =>
    resp.url().includes('/api/v1/organizations') && resp.request().method() === 'POST'
  );

  await page.locator('#new-org-form button[type="submit"], #submit-org-btn').click();

  // Wait for the API response
  const response = await responsePromise;
  const status = response.status();
  console.log('Organization creation status:', status);

  if (status !== 200 && status !== 201) {
    const body = await response.text();
    console.log('Organization creation failed:', body);
    throw new Error(`Failed to create organization: ${status}`);
  }

  // Wait for modal to close
  await modal.waitFor({ state: 'hidden', timeout: 5000 });

  // Wait for page to refresh the list
  await page.waitForTimeout(2000);

  // Verify org appears in list
  const orgVisible = await page.locator(`text="${orgName}"`).isVisible({ timeout: 5000 }).catch(() => false);
  console.log('Organization visible in list:', orgVisible);

  if (!orgVisible) {
    // Debug: log what orgs are visible
    const orgList = await page.locator('#organizations-list').textContent();
    console.log('Organizations list content:', orgList);

    // Refresh the page to try again
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

  // Wait for organizations API call to complete
  await page.waitForTimeout(2000);

  // Debug: log available options
  const options = await orgSelector.locator('option').allTextContents();
  console.log('Available org options:', options);

  // Check if our org is in the list
  const hasOrg = options.some(opt => opt.includes(orgName) || opt === orgName);
  if (!hasOrg) {
    console.log(`Organization "${orgName}" not found in dropdown. Available:`, options);
    // Try to refresh the page and wait for orgs to load again
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check again
    const newOptions = await orgSelector.locator('option').allTextContents();
    console.log('After reload, available org options:', newOptions);
  }

  // Select by text
  await orgSelector.selectOption({ label: orgName });
  await page.waitForTimeout(1000);
}

test.describe('Membership: Members', () => {

  test('user can create a member', async ({ page }) => {
    await setupUser(page, 'members');
    const orgName = `MemberTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // Navigate to members page
    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Select the organization
    await selectOrganization(page, orgName);

    // Click Add Member
    await page.locator('button:has-text("Add Member")').first().click();

    // Wait for modal to be visible
    await page.locator('#add-member-modal').waitFor({ state: 'visible', timeout: 5000 });

    // Fill in member details
    const memberName = `Test Member ${uniqueId()}`;
    await page.locator('#member-name').fill(memberName);
    await page.locator('#member-email').fill(`member_${uniqueId()}@test.com`);
    await page.locator('#member-phone').fill('555-1234');
    await page.locator('#member-status').selectOption('active');
    await page.locator('#member-type').selectOption('regular');
    await page.locator('#member-notes').fill('Test member created by Playwright');

    // Submit the form and wait for modal to close
    await page.locator('#submit-member-btn').click();

    // Wait for modal to close (indicates success)
    await page.locator('#add-member-modal').waitFor({ state: 'hidden', timeout: 10000 });

    // Wait for table to update with new member
    await page.waitForTimeout(1000);

    // Wait for the member to appear in the table
    await expect(page.locator(`text="${memberName}"`)).toBeVisible({ timeout: 10000 });
    console.log('Member visible in list: true');
  });

  test('user can edit a member', async ({ page }) => {
    await setupUser(page, 'memberedit');
    const orgName = `MemberEditTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // Navigate to members page
    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Create a member first
    const memberName = `Edit Test Member ${uniqueId()}`;
    await page.locator('button:has-text("Add Member")').first().click();
    await page.locator('#add-member-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#member-name').fill(memberName);
    await page.locator('#member-email').fill(`edit_${uniqueId()}@test.com`);
    await page.locator('#member-status').selectOption('active');
    await page.locator('#submit-member-btn').click();
    await page.locator('#add-member-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Wait for member to appear in table
    await expect(page.locator(`text="${memberName}"`)).toBeVisible({ timeout: 10000 });

    // Click Edit on the member
    const editBtn = page.locator(`tr:has-text("${memberName}") button:has-text("Edit")`).first();
    await editBtn.click();

    // Wait for edit modal to be visible
    await page.locator('#edit-member-modal').waitFor({ state: 'visible', timeout: 5000 });

    // Update member details
    const updatedName = `Updated Member ${uniqueId()}`;
    await page.locator('#edit-member-name').fill(updatedName);
    await page.locator('#edit-member-status').selectOption('inactive');

    // Save changes
    await page.locator('#submit-edit-member-btn').click();

    // Wait for modal to close
    await page.locator('#edit-member-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Verify the updated member appears
    await expect(page.locator(`text="${updatedName}"`)).toBeVisible({ timeout: 10000 });
    console.log('Updated member visible: true');
  });

  test('user can filter members by status', async ({ page }) => {
    await setupUser(page, 'memberfilter');
    const orgName = `MemberFilterTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/members.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Create members with different statuses
    const activeMember = `Active ${uniqueId()}`;
    const inactiveMember = `Inactive ${uniqueId()}`;

    // Create active member
    await page.locator('button:has-text("Add Member")').first().click();
    await page.locator('#add-member-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#member-name').fill(activeMember);
    await page.locator('#member-status').selectOption('active');
    await page.locator('#submit-member-btn').click();
    await page.locator('#add-member-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Create inactive member
    await page.locator('button:has-text("Add Member")').first().click();
    await page.locator('#add-member-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#member-name').fill(inactiveMember);
    await page.locator('#member-status').selectOption('inactive');
    await page.locator('#submit-member-btn').click();
    await page.locator('#add-member-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Filter by active
    await page.locator('button.filter-btn[data-status="active"]').click();
    await page.waitForTimeout(1500);

    // Active member should be visible
    await expect(page.locator(`text="${activeMember}"`)).toBeVisible({ timeout: 10000 });
    console.log('Active member visible with filter: true');
  });

});

test.describe('Membership: Contacts', () => {

  test('user can create a contact', async ({ page }) => {
    await setupUser(page, 'contacts');
    const orgName = `ContactTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/contacts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Click Add Contact
    await page.locator('button:has-text("Add Contact")').first().click();

    // Wait for modal to be visible
    await page.locator('#add-contact-modal').waitFor({ state: 'visible', timeout: 5000 });

    // Fill in contact details - using first_name and last_name fields (not contact-name)
    const firstName = 'Test';
    const lastName = `Contact ${uniqueId()}`;
    const companyName = `Company ${uniqueId()}`;
    await page.locator('#contact-first-name').fill(firstName);
    await page.locator('#contact-last-name').fill(lastName);
    await page.locator('#contact-company').fill(companyName);
    await page.locator('#contact-email').fill(`contact_${uniqueId()}@test.com`);
    await page.locator('#contact-type').selectOption('donor');

    // Wait for the API response to complete after clicking submit
    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/membership/contacts') && resp.request().method() === 'POST'
    );

    await page.locator('#submit-contact-btn').click();

    // Wait for the API response
    const response = await responsePromise;
    console.log('Contact creation response status:', response.status());

    // Wait for modal to have hidden class (Tailwind's hidden class = display: none)
    await expect(page.locator('#add-contact-modal')).toHaveClass(/hidden/, { timeout: 10000 });

    // Wait for table to update
    await page.waitForTimeout(1000);

    // Verify contact appears in the list (company name or full name should be visible)
    await expect(page.locator(`text="${companyName}"`)).toBeVisible({ timeout: 10000 });
    console.log('Contact visible in list: true');
  });

});

test.describe('Finance: Chart of Accounts', () => {

  test('user can create an account', async ({ page }) => {
    await setupUser(page, 'accounts');
    const orgName = `AccountTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_accounts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Click Add Account
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });

    const accountCode = `1${uniqueId().toString().slice(-3)}`;
    await page.locator('#account-code').fill(accountCode);
    await page.locator('#account-name').fill('Test Cash Account');
    await page.locator('#account-type').selectOption('asset');
    await page.locator('#account-subtype').selectOption('cash');
    await page.locator('#account-description').fill('Test account for e2e testing');

    await page.locator('#submit-account-btn').click();
    await page.locator('#add-account-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    await expect(page.locator(`text="${accountCode}"`)).toBeVisible({ timeout: 10000 });
    console.log('Account visible in list: true');
  });

  test('user can edit an account', async ({ page }) => {
    await setupUser(page, 'accountedit');
    const orgName = `AccountEditTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_accounts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Create an account first
    const accountCode = `2${uniqueId().toString().slice(-3)}`;
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#account-code').fill(accountCode);
    await page.locator('#account-name').fill('Original Account Name');
    await page.locator('#account-type').selectOption('expense');
    await page.locator('#submit-account-btn').click();
    await page.locator('#add-account-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Wait for account to appear in table
    await expect(page.locator(`text="${accountCode}"`)).toBeVisible({ timeout: 10000 });

    // Click Edit on the account
    const editBtn = page.locator(`tr:has-text("${accountCode}") button:has-text("Edit")`).first();
    await editBtn.click();

    // Wait for edit modal to be visible
    await page.locator('#edit-account-modal').waitFor({ state: 'visible', timeout: 5000 });

    // Update account name
    const updatedName = 'Updated Account Name';
    await page.locator('#edit-account-name').fill(updatedName);
    await page.locator('#submit-edit-account-btn').click();
    await page.locator('#edit-account-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    await expect(page.locator(`text="${updatedName}"`)).toBeVisible({ timeout: 10000 });
    console.log('Updated account visible: true');
  });

  test('user can filter accounts by type', async ({ page }) => {
    await setupUser(page, 'accountfilter');
    const orgName = `AccountFilterTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_accounts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Create accounts of different types
    const assetCode = `3${uniqueId().toString().slice(-3)}`;
    const expenseCode = `4${uniqueId().toString().slice(-3)}`;

    // Create asset account
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#account-code').fill(assetCode);
    await page.locator('#account-name').fill('Filter Test Asset');
    await page.locator('#account-type').selectOption('asset');
    await page.locator('#submit-account-btn').click();
    await page.locator('#add-account-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Create expense account
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#account-code').fill(expenseCode);
    await page.locator('#account-name').fill('Filter Test Expense');
    await page.locator('#account-type').selectOption('expense');
    await page.locator('#submit-account-btn').click();
    await page.locator('#add-account-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Filter by asset type
    await page.locator('button.filter-btn[data-type="asset"]').click();
    await page.waitForTimeout(1500);

    await expect(page.locator(`text="${assetCode}"`)).toBeVisible({ timeout: 10000 });
    console.log('Asset account visible with filter: true');
  });

});

test.describe('Finance: Donations', () => {

  test('user can record a donation', async ({ page }) => {
    await setupUser(page, 'donations');
    const orgName = `DonationTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_donations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Click Record Donation
    await page.locator('button:has-text("Record Donation")').first().click();
    await page.locator('#add-donation-modal').waitFor({ state: 'visible', timeout: 5000 });

    const donorName = `Test Donor ${uniqueId()}`;
    await page.locator('#donation-donor-name').fill(donorName);
    await page.locator('#donation-donor-email').fill(`donor_${uniqueId()}@test.com`);
    await page.locator('#donation-amount').fill('100.00');
    await page.locator('#donation-status').selectOption('received');
    await page.locator('#donation-payment').selectOption('cash');
    await page.locator('#donation-purpose').fill('General Fund');

    await page.locator('#submit-donation-btn').click();
    await page.locator('#add-donation-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    await expect(page.locator(`text="${donorName}"`)).toBeVisible({ timeout: 10000 });
    console.log('Donation visible in list: true');
  });

  test('donation summary cards update', async ({ page }) => {
    await setupUser(page, 'donationsummary');
    const orgName = `DonationSummaryTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_donations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Record a donation
    await page.locator('button:has-text("Record Donation")').first().click();
    await page.locator('#add-donation-modal').waitFor({ state: 'visible', timeout: 5000 });

    await page.locator('#donation-donor-name').fill(`Summary Test Donor ${uniqueId()}`);
    await page.locator('#donation-amount').fill('250.00');
    await page.locator('#donation-status').selectOption('received');
    await page.locator('#submit-donation-btn').click();
    await page.locator('#add-donation-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(2000);

    // Check that the Total Received card is not $0.00
    const totalReceived = await page.locator('#total-received').textContent();
    console.log('Total received:', totalReceived);

    // It should show a value greater than $0.00
    expect(totalReceived).not.toBe('$0.00');
  });

  test('user can filter donations by status', async ({ page }) => {
    await setupUser(page, 'donationfilter');
    const orgName = `DonationFilterTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    await page.goto('/pages/finance_donations.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Record donations with different statuses
    const receivedDonor = `Received Donor ${uniqueId()}`;
    const pendingDonor = `Pending Donor ${uniqueId()}`;

    // Record received donation
    await page.locator('button:has-text("Record Donation")').first().click();
    await page.locator('#add-donation-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#donation-donor-name').fill(receivedDonor);
    await page.locator('#donation-amount').fill('100.00');
    await page.locator('#donation-status').selectOption('received');
    await page.locator('#submit-donation-btn').click();
    await page.locator('#add-donation-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Record pending donation
    await page.locator('button:has-text("Record Donation")').first().click();
    await page.locator('#add-donation-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#donation-donor-name').fill(pendingDonor);
    await page.locator('#donation-amount').fill('50.00');
    await page.locator('#donation-status').selectOption('pending');
    await page.locator('#submit-donation-btn').click();
    await page.locator('#add-donation-modal').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Filter by received status
    await page.locator('button.filter-btn[data-status="received"]').click();
    await page.waitForTimeout(1500);

    await expect(page.locator(`text="${receivedDonor}"`)).toBeVisible({ timeout: 10000 });
    console.log('Received donation visible with filter: true');
  });

});

test.describe('Finance: Journal Entries', () => {

  test('user can create a journal entry', async ({ page }) => {
    await setupUser(page, 'journal');
    const orgName = `JournalTest Org ${uniqueId()}`;
    await createOrganization(page, orgName);

    // First create accounts for the journal entry
    await page.goto('/pages/finance_accounts.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Create Cash account
    const cashCode = `10${uniqueId().toString().slice(-2)}`;
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#account-code').fill(cashCode);
    await page.locator('#account-name').fill('Cash');
    await page.locator('#account-type').selectOption('asset');

    // Wait for the API response
    const cashResponsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/finance/accounts') && resp.request().method() === 'POST'
    );
    await page.locator('#submit-account-btn').click();
    const cashResponse = await cashResponsePromise;
    console.log('Cash account creation status:', cashResponse.status());

    // Wait for modal to have hidden class
    await expect(page.locator('#add-account-modal')).toHaveClass(/hidden/, { timeout: 10000 });
    await page.waitForTimeout(1000);

    // Create Donation Revenue account
    const revenueCode = `40${uniqueId().toString().slice(-2)}`;
    await page.locator('button:has-text("Add Account")').first().click();
    await page.locator('#add-account-modal').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#account-code').fill(revenueCode);
    await page.locator('#account-name').fill('Donation Revenue');
    await page.locator('#account-type').selectOption('revenue');

    // Wait for the API response
    const revenueResponsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/finance/accounts') && resp.request().method() === 'POST'
    );
    await page.locator('#submit-account-btn').click();
    const revenueResponse = await revenueResponsePromise;
    console.log('Revenue account creation status:', revenueResponse.status());

    // Wait for modal to have hidden class
    await expect(page.locator('#add-account-modal')).toHaveClass(/hidden/, { timeout: 10000 });
    await page.waitForTimeout(1000);

    // Now go to journal entries page
    await page.goto('/pages/finance_journal.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await selectOrganization(page, orgName);

    // Click New Journal Entry
    await page.locator('button:has-text("New Journal Entry")').first().click();

    // Wait for modal to be visible
    await page.locator('#new-entry-modal').waitFor({ state: 'visible', timeout: 5000 });

    // Fill in journal entry details - correct ID is #entry-description, not #journal-description
    const description = `Test donation received ${uniqueId()}`;
    await page.locator('#entry-description').fill(description);

    // The modal auto-adds 2 lines when opened, journal lines are in #journal-lines tbody
    // Wait for account selects to populate with options
    await page.waitForTimeout(1500);

    // Line 1: Debit Cash - select uses name pattern "lines[N][account_id]"
    const line1 = page.locator('#journal-lines tr').first();
    // Get all options and find the one containing cashCode
    const line1Select = line1.locator('select');
    const options1 = await line1Select.locator('option').allInnerTexts();
    const cashOption = options1.find(opt => opt.includes(cashCode));
    if (cashOption) {
      await line1Select.selectOption({ label: cashOption });
    }
    await line1.locator('input[name*="[debit]"]').fill('100.00');

    // Line 2: Credit Donation Revenue
    const line2 = page.locator('#journal-lines tr').nth(1);
    const line2Select = line2.locator('select');
    const options2 = await line2Select.locator('option').allInnerTexts();
    const revenueOption = options2.find(opt => opt.includes(revenueCode));
    if (revenueOption) {
      await line2Select.selectOption({ label: revenueOption });
    }
    await line2.locator('input[name*="[credit]"]').fill('100.00');

    // Wait for the journal entry API response
    const journalResponsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/finance/journal') && resp.request().method() === 'POST'
    );
    await page.locator('#submit-entry-btn').click();
    const journalResponse = await journalResponsePromise;
    console.log('Journal entry creation status:', journalResponse.status());

    // Wait for modal to have hidden class
    await expect(page.locator('#new-entry-modal')).toHaveClass(/hidden/, { timeout: 10000 });

    // Wait for table to update
    await page.waitForTimeout(1000);

    // Verify entry appears in list
    await expect(page.locator(`text="${description}"`)).toBeVisible({ timeout: 10000 });
    console.log('Journal entry visible in list: true');
  });

});
