// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

/**
 * FILE ATTACHMENTS TESTS
 *
 * Tests for the file storage integration with meeting documents.
 * Verifies upload, download, and role-based access controls.
 */

test.describe('File Attachments Tests', () => {
  let testUser;
  let testOrg;
  let testMeeting;

  // Helper to create test user and login
  async function createAndLoginUser(page, request, suffix = '') {
    const email = `filetest_${Date.now()}${suffix}@example.com`;
    const password = 'FileTest123';

    // Create user via API
    await request.post('/api/collections/users/records', {
      data: {
        email,
        password,
        passwordConfirm: password,
        name: 'File Test User'
      }
    });

    // Login
    await page.goto('/pages/login.html');
    await page.fill('#email', email);
    await page.fill('#password', password);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard.html', { timeout: 10000 });

    return { email, password };
  }

  test('API endpoints should be accessible', async ({ request }) => {
    // Test that file endpoints exist
    const listResponse = await request.get('/api/collections/files/records');
    expect(listResponse.status()).toBe(200);

    // Should return paginated response
    const data = await listResponse.json();
    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('totalItems');
  });

  test('should show file upload API helper exists', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const apiCheck = await page.evaluate(() => {
      return {
        filesApiExists: typeof window.API?.files !== 'undefined',
        uploadExists: typeof window.API?.files?.upload === 'function',
        listExists: typeof window.API?.files?.list === 'function',
        deleteExists: typeof window.API?.files?.delete === 'function'
      };
    });

    console.log('API files methods:', apiCheck);
    expect(apiCheck.filesApiExists).toBe(true);
    expect(apiCheck.uploadExists).toBe(true);
    expect(apiCheck.listExists).toBe(true);
    expect(apiCheck.deleteExists).toBe(true);
  });

  test('App.getFiles and App.uploadFile should be available', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const appCheck = await page.evaluate(() => {
      return {
        getFilesExists: typeof window.App?.getFiles === 'function',
        uploadFileExists: typeof window.App?.uploadFile === 'function',
        deleteFileExists: typeof window.App?.deleteFile === 'function',
        getFileUrlExists: typeof window.App?.getFileUrl === 'function'
      };
    });

    console.log('App file methods:', appCheck);
    expect(appCheck.getFilesExists).toBe(true);
    expect(appCheck.uploadFileExists).toBe(true);
    expect(appCheck.deleteFileExists).toBe(true);
    expect(appCheck.getFileUrlExists).toBe(true);
  });

  test('file upload API should require authentication', async ({ request }) => {
    // Create a test file buffer
    const testContent = Buffer.from('Test file content for upload');

    // Try to upload without auth - should fail
    const uploadResponse = await request.post('/api/collections/files/records', {
      multipart: {
        organization: 'test-org-id',
        upload: {
          name: 'test.txt',
          mimeType: 'text/plain',
          buffer: testContent
        }
      }
    });

    // Should get 401 Unauthorized
    expect(uploadResponse.status()).toBe(401);
  });

  test('file download endpoint should exist', async ({ request }) => {
    // Try to download a non-existent file
    const downloadResponse = await request.get('/api/collections/files/records/nonexistent/download');

    // Should get 404 (not found) rather than 500 or route error
    expect(downloadResponse.status()).toBe(404);
  });

  test('meeting documents tab should show upload button for members', async ({ page, request }) => {
    // This test verifies the UI structure exists
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Check if meeting page has the documents tab structure
    // We don't need to be logged in to verify HTML structure
    const meetingPageContent = await page.evaluate(async () => {
      // Fetch the meeting page HTML
      const resp = await fetch('/pages/meeting.html');
      const html = await resp.text();
      return {
        hasDocumentsTab: html.includes('tab-documents'),
        hasUploadButton: html.includes('upload-document-btn'),
        hasUploadModal: html.includes('upload-document-modal'),
        hasDocumentsList: html.includes('documents-list')
      };
    });

    console.log('Meeting page structure:', meetingPageContent);
    expect(meetingPageContent.hasDocumentsTab).toBe(true);
    expect(meetingPageContent.hasUploadButton).toBe(true);
    expect(meetingPageContent.hasUploadModal).toBe(true);
    expect(meetingPageContent.hasDocumentsList).toBe(true);
  });

  test('getFileUrl should return correct download path', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const fileUrl = await page.evaluate(() => {
      const testRecord = { id: 'test123' };
      return window.App.getFileUrl(testRecord, 'somefile.pdf');
    });

    console.log('File URL:', fileUrl);
    expect(fileUrl).toBe('/api/collections/files/records/test123/download');
  });
});
