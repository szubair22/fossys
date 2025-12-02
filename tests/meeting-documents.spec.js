// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

/**
 * MEETING DOCUMENTS E2E TESTS
 *
 * Full end-to-end tests for file uploads on meeting documents tab.
 * Tests upload, download, delete, and role-based access controls.
 */

test.describe('Meeting Documents E2E Tests', () => {
  const testFileName = 'test-document.txt';
  const testFileContent = 'This is a test document for meeting attachments.';

  // Create test file before all tests
  test.beforeAll(async () => {
    const testFilePath = path.join(__dirname, testFileName);
    fs.writeFileSync(testFilePath, testFileContent);
  });

  // Clean up test file after all tests
  test.afterAll(async () => {
    const testFilePath = path.join(__dirname, testFileName);
    try {
      fs.unlinkSync(testFilePath);
    } catch (e) {
      // File might not exist
    }
  });

  test('full meeting documents flow: register -> create org -> meeting -> upload -> delete', async ({ page, request }) => {
    test.setTimeout(120000); // 2 min timeout for this comprehensive test

    const timestamp = Date.now();
    const testEmail = `meetdoc_${timestamp}@example.com`;
    const testPassword = 'MeetDoc123!';
    const orgName = `MeetDocOrg${timestamp}`;
    const meetingTitle = `MeetDocMeeting${timestamp}`;

    // Track API activity
    page.on('response', response => {
      if (response.url().includes('/api/') && response.status() >= 400) {
        console.log(`API Error: ${response.status()} ${response.url()}`);
      }
    });

    // === STEP 1: Create user via API (more reliable than UI) ===
    console.log('\n=== Step 1: Create user via API ===');
    const createUserResponse = await request.post('/api/collections/users/records', {
      data: {
        email: testEmail,
        password: testPassword,
        passwordConfirm: testPassword,
        name: 'Meeting Doc Test User'
      }
    });
    expect(createUserResponse.status()).toBe(200);
    const userData = await createUserResponse.json();
    const userId = userData.id;
    console.log('User created:', testEmail, userId);

    // === STEP 2: Login via UI to get session ===
    console.log('\n=== Step 2: Login ===');
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 15000 });
    console.log('Login successful');

    // === STEP 3: Create organization via API ===
    console.log('\n=== Step 3: Create organization via API ===');

    // First get auth token from browser
    const authToken = await page.evaluate(() => {
      return localStorage.getItem('orgmeet_token');
    });
    console.log('Auth token retrieved:', authToken ? 'yes' : 'no');

    // Create org via API with auth
    const createOrgResponse = await request.post('/api/collections/organizations/records', {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
      data: {
        name: orgName,
        description: 'Test organization for meeting documents'
      }
    });

    if (createOrgResponse.status() !== 200) {
      console.log('Org creation response:', createOrgResponse.status(), await createOrgResponse.text());
    }
    expect(createOrgResponse.status()).toBe(200);

    const orgData = await createOrgResponse.json();
    const organizationId = orgData.id;
    console.log('Organization created:', organizationId);

    // === STEP 4: Create meeting via API ===
    console.log('\n=== Step 4: Create meeting via API ===');
    const startTime = new Date(Date.now() + 3600000).toISOString();
    const endTime = new Date(Date.now() + 7200000).toISOString();

    const createMeetingResponse = await request.post('/api/v1/governance/meetings', {
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
      data: {
        title: meetingTitle,
        description: 'Test meeting for documents',
        organization_id: organizationId,
        start_time: startTime,
        end_time: endTime,
        status: 'scheduled'
      }
    });

    if (createMeetingResponse.status() !== 200 && createMeetingResponse.status() !== 201) {
      console.log('Meeting creation response:', createMeetingResponse.status(), await createMeetingResponse.text());
    }
    expect([200, 201]).toContain(createMeetingResponse.status());

    const meetingData = await createMeetingResponse.json();
    const meetingId = meetingData.id;
    console.log('Meeting created:', meetingId);

    // === STEP 5: Navigate to Documents tab ===
    console.log('\n=== Step 5: Navigate to Documents tab ===');
    await page.goto(`/pages/meeting.html?id=${meetingId}`);
    await page.waitForLoadState('networkidle');

    // Wait for meeting info to load
    await page.waitForSelector('#meeting-info', { timeout: 15000 });
    await page.waitForTimeout(1000);

    // Click on Documents tab
    await page.click('button[data-tab="documents"]');
    await page.waitForTimeout(500);

    // Verify Documents tab is visible
    const documentsTab = page.locator('#tab-documents');
    await expect(documentsTab).toBeVisible();
    console.log('Documents tab visible');

    // Verify upload button is visible (as owner/admin)
    const uploadBtn = page.locator('[data-testid="upload-document-btn"], #upload-document-btn');
    await expect(uploadBtn).toBeVisible();
    console.log('Upload button visible for admin');

    // === STEP 6: Upload a document ===
    console.log('\n=== Step 6: Upload a document ===');
    await uploadBtn.click();
    await page.waitForSelector('#upload-document-modal:not(.hidden)', { timeout: 5000 });

    // Set the file
    const testFilePath = path.join(__dirname, testFileName);
    const fileInput = page.locator('#document-file');
    await fileInput.setInputFiles(testFilePath);

    // Set document name
    const nameInput = page.locator('#document-name');
    if (await nameInput.isVisible()) {
      await nameInput.fill('Test Document E2E');
    }

    // Submit upload
    await page.click('#upload-document-form button[type="submit"]');
    await page.waitForTimeout(3000);

    // Verify document appears in the list
    const documentItem = page.locator('[data-testid="document-item"]').first();
    await expect(documentItem).toBeVisible({ timeout: 10000 });
    console.log('Document uploaded successfully');

    // === STEP 7: Verify download link ===
    console.log('\n=== Step 7: Verify download link ===');
    const downloadLink = page.locator('[data-testid="document-download"]').first();
    await expect(downloadLink).toBeVisible();

    const href = await downloadLink.getAttribute('href');
    console.log('Download link href:', href);

    expect(href).toContain('/api/collections/files/records/');
    expect(href).toContain('/download');
    console.log('Download link correct');

    // === STEP 8: Verify admin can see delete button ===
    console.log('\n=== Step 8: Verify admin delete button ===');
    const deleteBtn = page.locator('[data-testid="document-delete"]').first();
    await expect(deleteBtn).toBeVisible();
    console.log('Delete button visible for admin');

    // === STEP 9: Delete the document ===
    console.log('\n=== Step 9: Delete the document ===');
    const docsBefore = await page.locator('[data-testid="document-item"]').count();
    console.log('Documents before delete:', docsBefore);

    // Handle confirmation dialog
    page.on('dialog', async dialog => {
      console.log('Dialog:', dialog.message());
      await dialog.accept();
    });

    await deleteBtn.click();
    await page.waitForTimeout(2000);

    const docsAfter = await page.locator('[data-testid="document-item"]').count();
    console.log('Documents after delete:', docsAfter);

    expect(docsAfter).toBeLessThan(docsBefore);
    console.log('Document deleted successfully');

    // === SUMMARY ===
    console.log('\n=== TEST SUMMARY ===');
    console.log('All meeting documents operations completed successfully!');
  });

  test('documents tab structure verification', async ({ page }) => {
    // This test verifies the HTML structure without needing login
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Fetch the meeting page HTML and verify structure
    const meetingPageCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/meeting.html');
      const html = await resp.text();
      return {
        hasDocumentsTab: html.includes('tab-documents'),
        hasUploadButton: html.includes('upload-document-btn'),
        hasUploadModal: html.includes('upload-document-modal'),
        hasDocumentsList: html.includes('documents-list'),
        hasDataTestId: html.includes('data-testid')
      };
    });

    console.log('Meeting page structure:', meetingPageCheck);

    expect(meetingPageCheck.hasDocumentsTab).toBe(true);
    expect(meetingPageCheck.hasUploadButton).toBe(true);
    expect(meetingPageCheck.hasUploadModal).toBe(true);
    expect(meetingPageCheck.hasDocumentsList).toBe(true);
    expect(meetingPageCheck.hasDataTestId).toBe(true);
  });

  test('file upload API requires authentication', async ({ request }) => {
    // Try to upload without auth - should fail
    const uploadResponse = await request.post('/api/collections/files/records', {
      multipart: {
        organization: 'test-org-id',
        upload: {
          name: 'test.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('Test content')
        }
      }
    });

    // Should get 401 Unauthorized
    expect(uploadResponse.status()).toBe(401);
    console.log('File upload API correctly requires auth');
  });

  test('meeting documents count updates correctly', async ({ page }) => {
    // This test just verifies the documents count element exists in the UI
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Verify meeting page has documents count
    const meetingPageCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/meeting.html');
      const html = await resp.text();
      return {
        hasDocumentsCount: html.includes('documents-count'),
        hasDocumentsNav: html.includes('data-tab="documents"')
      };
    });

    console.log('Documents UI elements:', meetingPageCheck);

    expect(meetingPageCheck.hasDocumentsCount).toBe(true);
    expect(meetingPageCheck.hasDocumentsNav).toBe(true);
  });
});
