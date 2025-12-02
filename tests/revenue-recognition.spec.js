// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * REVENUE RECOGNITION E2E TESTS
 *
 * Tests for ASC 606-lite Revenue Recognition features:
 * - Contract creation with lines
 * - Transaction price allocation
 * - Schedule generation (straight-line and point-in-time)
 * - Revenue recognition runs
 * - Waterfall reporting
 * - Edition gating (nonprofit vs startup)
 */

// Helper to generate unique test data
const uniqueId = () => Date.now();

// Helper to format dates for API calls
const formatDate = (date) => {
  return date.toISOString().split('T')[0];
};

// Helper to login or register a user
async function setupUser(page, prefix = 'test') {
  const email = `${prefix}_${uniqueId()}@example.com`;
  const password = 'TestPass123';

  await page.goto('/pages/register.html');
  await page.waitForLoadState('domcontentloaded');

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
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  await page.locator('button:has-text("Create Organization")').first().click();

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
  if (response.status() !== 200 && response.status() !== 201) {
    throw new Error(`Failed to create organization: ${response.status()}`);
  }

  await modal.waitFor({ state: 'hidden', timeout: 5000 });
  await page.waitForTimeout(1000);

  // Get org ID from API
  const orgsResponse = await page.evaluate(async () => {
    const token = window.App?.pb?.authStore?.token;
    if (!token) return null;
    const resp = await fetch('/api/v1/organizations', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
  });

  if (orgsResponse && orgsResponse.items && orgsResponse.items.length > 0) {
    const org = orgsResponse.items.find(o => o.name === orgName);
    return org?.id || orgsResponse.items[0].id;
  }
  return null;
}

// Helper to get auth token from page
async function getAuthToken(page) {
  return await page.evaluate(() => {
    return window.App?.pb?.authStore?.token || localStorage.getItem('orgmeet_token');
  });
}

// Helper to switch organization to nonprofit edition
async function switchToNonprofitEdition(page, orgName) {
  await page.goto('/pages/admin_finance.html');
  await page.waitForLoadState('domcontentloaded');
  // Wait for options to be attached (not visible - options inside <select> are hidden until dropdown is opened)
  await page.waitForSelector('[data-testid="org-selector"] option:not([value=""])', { state: 'attached' });
  await page.locator('[data-testid="org-selector"]').selectOption({ label: orgName });
  await page.waitForTimeout(1500);

  await page.locator('[data-testid="edition-nonprofit-card"]').click();
  await page.waitForTimeout(500);

  await page.locator('[data-testid="save-settings-btn"]').click();
  // Accept either legacy or by-key endpoint for saving settings
  await Promise.any([
    page.waitForResponse(resp => resp.url().includes('/api/v1/admin/org-settings/by-key') && resp.request().method() === 'PUT'),
    page.waitForResponse(resp => resp.url().includes('/api/v1/admin/org-settings') && resp.request().method() === 'PUT')
  ]);
  await page.waitForTimeout(500);
}

// Helper to create required accounts for contracts
async function createContractAccounts(page, orgId, token) {
  // Create revenue account
  const revenueResponse = await page.request.post(
    `/api/v1/finance/accounts?organization_id=${orgId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      data: {
        code: `4${uniqueId().toString().slice(-3)}`,
        name: 'Service Revenue',
        account_type: 'revenue',
        account_subtype: 'other_income'
      }
    }
  );
  const revenueAccount = await revenueResponse.json();

  // Create deferred revenue account
  const deferredResponse = await page.request.post(
    `/api/v1/finance/accounts?organization_id=${orgId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      data: {
        code: `24${uniqueId().toString().slice(-2)}`,
        name: 'Deferred Revenue',
        account_type: 'liability',
        account_subtype: 'other_liability'
      }
    }
  );
  const deferredAccount = await deferredResponse.json();

  return { revenueAccount, deferredAccount };
}

// Helper to create a customer contact
async function createCustomerContact(page, orgId, token) {
  const response = await page.request.post(
    `/api/v1/membership/contacts?organization_id=${orgId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` },
      data: {
        first_name: 'Acme',
        last_name: 'Corp',
        email: `acme_${uniqueId()}@example.com`,
        contact_type: 'customer',
        is_active: true
      }
    }
  );
  return await response.json();
}


// ============================================================================
// CONTRACT CREATION TESTS
// ============================================================================

test.describe('Revenue Recognition: Contract Creation', () => {

  test('can create a contract with single line via UI', async ({ page }) => {
    await setupUser(page, 'contractui');
    const orgName = `Contract UI Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Switch to nonprofit edition
    await switchToNonprofitEdition(page, orgName);

    // Get token and create accounts + contact
    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    // Navigate to contracts page
    await page.goto(`/pages/finance_contracts.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');

    // Verify content is visible (not blocked by edition)
    const content = page.locator('[data-testid="contracts-content"]');
    await expect(content).toBeVisible({ timeout: 20000 });

    // Click New Contract button
    await page.locator('[data-testid="new-contract-btn"]').click();
    await page.locator('[data-testid="add-contract-modal"]').waitFor({ state: 'visible', timeout: 5000 });

    // Fill contract details using data-testid attributes
    const contractName = `Test Contract ${uniqueId()}`;
    const form = page.locator('[data-testid="add-contract-form"]');
    await page.locator('[data-testid="contract-name"]').fill(contractName);

    const today = new Date();
    const endDate = new Date(today);
    endDate.setFullYear(endDate.getFullYear() + 1);

    await page.locator('[data-testid="contract-start-date"]').fill(formatDate(today));
    await page.locator('[data-testid="contract-end-date"]').fill(formatDate(endDate));
    await page.locator('[data-testid="contract-total-price"]').fill('12000.00');

    // The page already shows a line added by default
    // Fill the existing line details using data-testid attributes
    await page.locator('[data-testid="line-description-0"]').fill('Annual Service');
    await page.locator('[data-testid="line-recognition-0"]').selectOption('straight_line');
    await page.locator('[data-testid="line-quantity-0"]').fill('1');
    await page.locator('[data-testid="line-unit-price-0"]').fill('12000.00');
    await page.locator('[data-testid="line-ssp-0"]').fill('12000.00');

    // Select revenue and deferred accounts from dropdowns (first non-empty option)
    await page.locator('[data-testid="line-revenue-account-0"]').selectOption({ index: 1 });
    await page.locator('[data-testid="line-deferred-account-0"]').selectOption({ index: 1 });

    // Submit the form
    const responsePromise = page.waitForResponse(resp =>
      resp.url().includes('/api/v1/finance/contracts') && resp.request().method() === 'POST'
    );

    await page.locator('[data-testid="submit-contract-btn"]').click();

    const response = await responsePromise;
    expect(response.status()).toBe(201);

    // Wait for modal to close
    await page.locator('[data-testid="add-contract-modal"]').waitFor({ state: 'hidden', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Verify contract appears in list
    await expect(page.locator(`text="${contractName}"`)).toBeVisible({ timeout: 10000 });
  });

  test('can create contract with multiple lines via API', async ({ page }) => {
    await setupUser(page, 'contractapi');
    const orgName = `Contract API Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();
    const endDate = new Date(today);
    endDate.setFullYear(endDate.getFullYear() + 1);

    // Create contract with multiple lines
    const contractData = {
      organization_id: orgId,
      name: `Multi-Line Contract ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      end_date: formatDate(endDate),
      total_transaction_price: 15000.00,
      currency: 'USD',
      lines: [
        {
          description: 'Software License',
          product_type: 'license',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 5000.00,
          ssp_amount: 6000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        },
        {
          description: 'Support Services',
          product_type: 'service',
          recognition_pattern: 'straight_line',
          start_date: formatDate(today),
          end_date: formatDate(endDate),
          quantity: 1,
          unit_price: 10000.00,
          ssp_amount: 10000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const response = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );

    expect(response.status()).toBe(201);
    const contract = await response.json();
    expect(contract.lines.length).toBe(2);
  });

});


// ============================================================================
// CONTRACT ACTIVATION AND ALLOCATION TESTS
// ============================================================================

test.describe('Revenue Recognition: Contract Activation', () => {

  test('activating contract allocates transaction price using SSP', async ({ page }) => {
    await setupUser(page, 'activate');
    const orgName = `Activate Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();
    const endDate = new Date(today);
    endDate.setFullYear(endDate.getFullYear() + 1);

    // Create contract with bundle discount
    // Total: $15,000, but SSPs total $16,000
    // Line 1: SSP $6,000 -> allocation: 6000/16000 * 15000 = $5,625
    // Line 2: SSP $10,000 -> allocation: 10000/16000 * 15000 = $9,375
    const contractData = {
      organization_id: orgId,
      name: `Allocation Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      end_date: formatDate(endDate),
      total_transaction_price: 15000.00,
      lines: [
        {
          description: 'License',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 5000.00,
          ssp_amount: 6000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        },
        {
          description: 'Support',
          recognition_pattern: 'straight_line',
          start_date: formatDate(today),
          end_date: formatDate(endDate),
          quantity: 1,
          unit_price: 10000.00,
          ssp_amount: 10000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    // Activate contract
    const activateResponse = await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: { generate_schedules: false }
      }
    );

    expect(activateResponse.status()).toBe(200);
    const activateResult = await activateResponse.json();
    expect(activateResult.status).toBe('active');

    // Fetch the full contract to verify allocation
    const getContractResponse = await page.request.get(
      `/api/v1/finance/contracts/${contract.id}?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    expect(getContractResponse.status()).toBe(200);
    const activatedContract = await getContractResponse.json();

    // Verify allocation
    const licenseLine = activatedContract.lines.find(l => l.description === 'License');
    const supportLine = activatedContract.lines.find(l => l.description === 'Support');

    expect(parseFloat(licenseLine.allocated_transaction_price)).toBe(5625.00);
    expect(parseFloat(supportLine.allocated_transaction_price)).toBe(9375.00);

    // Total should match
    const total = parseFloat(licenseLine.allocated_transaction_price) +
                  parseFloat(supportLine.allocated_transaction_price);
    expect(total).toBe(15000.00);
  });

});


// ============================================================================
// SCHEDULE GENERATION TESTS
// ============================================================================

test.describe('Revenue Recognition: Schedule Generation', () => {

  test('generates 12-month straight-line schedule', async ({ page }) => {
    await setupUser(page, 'schedule');
    const orgName = `Schedule Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    // Use fixed dates for predictable schedule
    const startDate = new Date(2025, 0, 1);  // Jan 1, 2025
    const endDate = new Date(2025, 11, 31);  // Dec 31, 2025

    // Create and activate contract
    const contractData = {
      organization_id: orgId,
      name: `12-Month Schedule Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(startDate),
      end_date: formatDate(endDate),
      total_transaction_price: 12000.00,
      lines: [
        {
          description: 'Annual Service',
          recognition_pattern: 'straight_line',
          start_date: formatDate(startDate),
          end_date: formatDate(endDate),
          quantity: 1,
          unit_price: 12000.00,
          ssp_amount: 12000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    // Activate with generate_schedules=false since we want to test generate-schedules endpoint
    await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: false } }
    );

    // Generate schedules explicitly
    const generateResponse = await page.request.post(
      `/api/v1/finance/revenue-recognition/generate-schedules?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: { contract_id: contract.id }
      }
    );

    expect(generateResponse.status()).toBe(200);
    const generateResult = await generateResponse.json();
    expect(generateResult.schedules_created).toBe(1);

    // Get schedules list (lines are empty in list view)
    const schedulesResponse = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}&contract_id=${contract.id}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    const schedules = await schedulesResponse.json();
    expect(schedules.items.length).toBe(1);

    // Get individual schedule to fetch lines
    const scheduleId = schedules.items[0].id;
    const scheduleResponse = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules/${scheduleId}?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const schedule = await scheduleResponse.json();
    expect(schedule.recognition_method).toBe('straight_line');
    expect(schedule.lines.length).toBe(12);

    // Each month should be $1,000
    for (const line of schedule.lines) {
      expect(parseFloat(line.amount)).toBe(1000.00);
    }
  });

  test('generates point-in-time single recognition', async ({ page }) => {
    await setupUser(page, 'pointschedule');
    const orgName = `Point Schedule Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();

    // Create and activate point-in-time contract
    const contractData = {
      organization_id: orgId,
      name: `Point-in-Time Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      total_transaction_price: 5000.00,
      lines: [
        {
          description: 'License',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 5000.00,
          ssp_amount: 5000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    // Activate - schedules generated automatically via generate_schedules=true
    await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    // Get schedules list (lines are empty in list view)
    const schedulesResponse = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}&contract_id=${contract.id}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );

    const schedules = await schedulesResponse.json();

    // Get individual schedule to fetch lines
    const scheduleId = schedules.items[0].id;
    const scheduleResponse = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules/${scheduleId}?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    );
    const schedule = await scheduleResponse.json();

    expect(schedule.recognition_method).toBe('point_in_time');
    expect(schedule.lines.length).toBe(1);
    expect(parseFloat(schedule.lines[0].amount)).toBe(5000.00);
  });

});


// ============================================================================
// REVENUE RECOGNITION RUN TESTS
// ============================================================================

test.describe('Revenue Recognition: Recognition Run', () => {

  test('dry run shows preview without creating journal entries', async ({ page }) => {
    await setupUser(page, 'dryrun');
    const orgName = `Dry Run Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();

    // Create point-in-time contract (recognizes immediately)
    const contractData = {
      organization_id: orgId,
      name: `Dry Run Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      total_transaction_price: 1000.00,
      lines: [
        {
          description: 'Service',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 1000.00,
          ssp_amount: 1000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    // Activate with generate_schedules=true (schedules created automatically)
    await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    // Run dry run (organization_id in body, not query param)
    const runResponse = await page.request.post(
      `/api/v1/finance/revenue-recognition/run`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          as_of_date: formatDate(today),
          dry_run: true
        }
      }
    );

    expect(runResponse.status()).toBe(200);
    const result = await runResponse.json();

    expect(result.lines_processed).toBeGreaterThanOrEqual(1);
    expect(parseFloat(result.total_amount)).toBe(1000.00);
    expect(result.journal_entries_created).toBe(0);  // Dry run = no entries
  });

  test('actual run creates journal entries', async ({ page }) => {
    await setupUser(page, 'actualrun');
    const orgName = `Actual Run Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();

    // Create contract
    const contractData = {
      organization_id: orgId,
      name: `Actual Run Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      total_transaction_price: 2500.00,
      lines: [
        {
          description: 'Service',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 2500.00,
          ssp_amount: 2500.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    // Activate with generate_schedules=true (schedules created automatically)
    await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    // Run actual recognition (organization_id in body)
    const runResponse = await page.request.post(
      `/api/v1/finance/revenue-recognition/run`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          as_of_date: formatDate(today),
          dry_run: false
        }
      }
    );

    expect(runResponse.status()).toBe(200);
    const result = await runResponse.json();

    expect(result.lines_posted).toBeGreaterThanOrEqual(1);
    expect(result.journal_entries_created).toBeGreaterThanOrEqual(1);
    expect(result.journal_entry_ids.length).toBeGreaterThanOrEqual(1);
  });

});


// ============================================================================
// UI NAVIGATION TESTS
// ============================================================================

test.describe('Revenue Recognition: UI Navigation', () => {

  test('rev rec page shows schedules after generation', async ({ page }) => {
    await setupUser(page, 'revrecui');
    const orgName = `Rev Rec UI Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    const today = new Date();

    // Create, activate, and generate schedule via API
    const contractData = {
      organization_id: orgId,
      name: `UI Test Contract ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      total_transaction_price: 3000.00,
      lines: [
        {
          description: 'UI Test Service',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 3000.00,
          ssp_amount: 3000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    expect(createResponse.status()).toBe(201);
    const contract = await createResponse.json();

    // Activate contract (generates schedules automatically if rev_rec is enabled)
    const activateResponse = await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: { generate_schedules: true }
      }
    );
    expect(activateResponse.status()).toBe(200);
    const activateResult = await activateResponse.json();
    // The activate endpoint generates schedules when generate_schedules=true
    expect(activateResult.schedules_generated).toBeGreaterThanOrEqual(1);

    // Wait until schedules are queryable (avoid racing backend writes)
    for (let i = 0; i < 10; i++) {
      const schedResp = await page.request.get(
        `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      if (schedResp.ok()) {
        const schedData = await schedResp.json();
        if ((schedData.items || []).length > 0) break;
      }
      await page.waitForTimeout(1000);
    }

    // Navigate to rev rec page
    await page.goto(`/pages/finance_rev_rec.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Content should be visible
    const content = page.locator('[data-testid="rev-rec-content"]');
    await expect(content).toBeVisible();

    // Schedules list visible
    await expect(page.locator('[data-testid="schedules-list"]')).toBeVisible({ timeout: 10000 });
      // Assert that at least one real schedule row is visible
      await expect(page.locator('[data-testid="schedule-row"]').first()).toBeVisible({ timeout: 15000 });
  });

  test('waterfall table displays revenue periods', async ({ page }) => {
    await setupUser(page, 'waterfall');
    const orgName = `Waterfall Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    // Use fixed dates for predictable waterfall
    const startDate = new Date(2025, 0, 1);
    const endDate = new Date(2025, 5, 30);  // 6 months

    // Create 6-month contract
    const contractData = {
      organization_id: orgId,
      name: `Waterfall Test ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(startDate),
      end_date: formatDate(endDate),
      total_transaction_price: 6000.00,
      lines: [
        {
          description: 'Waterfall Service',
          recognition_pattern: 'straight_line',
          start_date: formatDate(startDate),
          end_date: formatDate(endDate),
          quantity: 1,
          unit_price: 6000.00,
          ssp_amount: 6000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    const contract = await createResponse.json();

    await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    await page.request.post(
      `/api/v1/finance/revenue-recognition/generate-schedules?organization_id=${orgId}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: { contract_id: contract.id }
      }
    );

    // Navigate to rev rec page
    await page.goto(`/pages/finance_rev_rec.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Content should be visible (nonprofit edition enabled)
    const content = page.locator('[data-testid="rev-rec-content"]');
    await expect(content).toBeVisible();

    // Load waterfall by clicking the button
    await page.locator('[data-testid="load-waterfall-btn"]').click();
    await page.waitForTimeout(2000);

    // Waterfall body should have loaded data
    const waterfallBody = page.locator('[data-testid="waterfall-body"]');
    await expect(waterfallBody).toBeVisible();

    // Should have rows for at least some months (or the placeholder row)
    const rows = waterfallBody.locator('tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(1);
  });

});


// ============================================================================
// EDITION GATING TESTS (These complement the edition-mode.spec.js tests)
// ============================================================================

test.describe('Revenue Recognition: Edition Gating', () => {

  test('contracts API blocked for startup edition org', async ({ page }) => {
    await setupUser(page, 'startupblock');
    const orgName = `Startup Block Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Don't switch to nonprofit - stay on startup edition
    const token = await getAuthToken(page);

    const response = await page.request.get(
      `/api/v1/finance/contracts?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    expect(response.status()).toBe(403);
    const body = await response.json();
    expect(body.detail.toLowerCase()).toContain('not enabled');
  });

  test('rev rec API blocked for startup edition org', async ({ page }) => {
    await setupUser(page, 'revrecblock');
    const orgName = `Rev Rec Block Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    const token = await getAuthToken(page);

    const response = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    expect(response.status()).toBe(403);
  });

  test('contracts API accessible after switching to nonprofit', async ({ page }) => {
    await setupUser(page, 'nonprofitaccess');
    const orgName = `Nonprofit Access Org ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Switch to nonprofit
    await switchToNonprofitEdition(page, orgName);

    const token = await getAuthToken(page);

    const response = await page.request.get(
      `/api/v1/finance/contracts?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('items');
  });

});


// ============================================================================
// HAPPY PATH SMOKE TESTS
// ============================================================================

test.describe('Revenue Recognition: Happy Path Smoke Tests', () => {

  test('Nonprofit Edition: full revenue recognition flow', async ({ page }) => {
    // This is an end-to-end smoke test for nonprofit organizations
    // Create contract → Generate schedule → Run recognition → Verify waterfall
    await setupUser(page, 'nonprofit_smoke');
    const orgName = `Nonprofit Smoke Test ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Switch to nonprofit edition
    await switchToNonprofitEdition(page, orgName);

    // Get token and create accounts + contact
    const token = await getAuthToken(page);
    const { revenueAccount, deferredAccount } = await createContractAccounts(page, orgId, token);
    const contact = await createCustomerContact(page, orgId, token);

    // Step 1: Create a multi-line contract via API
    const today = new Date();
    const endDate = new Date(today);
    endDate.setFullYear(endDate.getFullYear() + 1);

    const contractData = {
      organization_id: orgId,
      name: `Smoke Test Contract ${uniqueId()}`,
      customer_contact_id: contact.id,
      start_date: formatDate(today),
      end_date: formatDate(endDate),
      total_transaction_price: 18000.00,
      currency: 'USD',
      lines: [
        {
          description: 'Annual Support',
          product_type: 'service',
          recognition_pattern: 'straight_line',
          start_date: formatDate(today),
          end_date: formatDate(endDate),
          quantity: 1,
          unit_price: 12000.00,
          ssp_amount: 12000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        },
        {
          description: 'Setup Fee',
          product_type: 'service',
          recognition_pattern: 'point_in_time',
          start_date: formatDate(today),
          quantity: 1,
          unit_price: 6000.00,
          ssp_amount: 6000.00,
          revenue_account_id: revenueAccount.id,
          deferred_revenue_account_id: deferredAccount.id
        }
      ]
    };

    const createResponse = await page.request.post(
      `/api/v1/finance/contracts`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: contractData
      }
    );
    expect(createResponse.status()).toBe(201);
    const contract = await createResponse.json();
    expect(contract.lines.length).toBe(2);

    // Step 2: Activate contract with generate_schedules=true (creates schedules automatically)
    const activateResponse = await page.request.post(
      `/api/v1/finance/contracts/${contract.id}/activate?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );
    expect(activateResponse.status()).toBe(200);
    const activatedContract = await activateResponse.json();
    expect(activatedContract.status).toBe('active');
    // Schedules are auto-generated: verify 2 schedules were created
    expect(activatedContract.schedules_generated).toBe(2);

    // Step 3: Run revenue recognition (organization_id in body)
    const runResponse = await page.request.post(
      `/api/v1/finance/revenue-recognition/run`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          organization_id: orgId,
          as_of_date: formatDate(today),
          dry_run: false
        }
      }
    );
    expect(runResponse.status()).toBe(200);
    const runResult = await runResponse.json();
    expect(runResult.lines_posted).toBeGreaterThanOrEqual(1);
    expect(runResult.journal_entries_created).toBeGreaterThanOrEqual(1);

    // Step 5: Verify waterfall in UI
    await page.goto(`/pages/finance_rev_rec.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Content should be visible (nonprofit edition)
    await expect(page.locator('[data-testid="rev-rec-content"]')).toBeVisible();

    // Schedules should be listed
    await expect(page.locator('[data-testid="schedules-list"]')).toBeVisible();

    // Load waterfall
    await page.locator('[data-testid="load-waterfall-btn"]').click();
    await page.waitForTimeout(2000);

    // Waterfall should display data
    const waterfallBody = page.locator('[data-testid="waterfall-body"]');
    await expect(waterfallBody).toBeVisible();
    const rows = await waterfallBody.locator('tr').count();
    expect(rows).toBeGreaterThanOrEqual(1);
  });

  test('Startup Edition: contracts and rev rec are blocked', async ({ page }) => {
    // This verifies startup edition gating in both UI and API
    await setupUser(page, 'startup_smoke');
    const orgName = `Startup Smoke Test ${uniqueId()}`;
    const orgId = await createOrganization(page, orgName);

    // Don't switch to nonprofit - stay on startup edition
    const token = await getAuthToken(page);

    // Step 1: Verify contracts API is blocked
    const contractsResponse = await page.request.get(
      `/api/v1/finance/contracts?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );
    expect(contractsResponse.status()).toBe(403);

    // Step 2: Verify rev rec API is blocked
    const revRecResponse = await page.request.get(
      `/api/v1/finance/revenue-recognition/schedules?organization_id=${orgId}`,
      { headers: { 'Authorization': `Bearer ${token}` }, data: { generate_schedules: true } }
    );
    expect(revRecResponse.status()).toBe(403);

    // Step 3: Verify contracts page shows edition warning
    await page.goto(`/pages/finance_contracts.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Edition warning should be visible
    await expect(page.locator('[data-testid="edition-warning"]')).toBeVisible();

    // Contracts content should be hidden
    await expect(page.locator('[data-testid="contracts-content"]')).toBeHidden();

    // Step 4: Verify rev rec page shows edition warning
    await page.goto(`/pages/finance_rev_rec.html?org=${orgId}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    // Edition warning should be visible
    await expect(page.locator('[data-testid="edition-warning"]')).toBeVisible();

    // Rev rec content should be hidden
    await expect(page.locator('[data-testid="rev-rec-content"]')).toBeHidden();
  });

});
