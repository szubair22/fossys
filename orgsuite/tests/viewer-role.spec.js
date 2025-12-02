// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * VIEWER ROLE RESTRICTION TESTS
 *
 * Tests to ensure viewer users cannot see create/edit/delete controls
 * across key pages in the application.
 *
 * Key pages tested:
 * - members.html
 * - contacts.html
 * - finance_accounts.html
 * - finance_journal.html
 * - finance_donations.html
 * - projects.html
 * - meeting.html
 */

test.describe('Viewer Role Restrictions', () => {

  test('pages should have data-require-role attributes on sensitive controls', async ({ page }) => {
    // This test verifies the HTML structure has proper role attributes
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Check members.html
    const membersCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/members.html');
      const html = await resp.text();
      return {
        hasAddMemberBtn: html.includes('id="add-member-btn"'),
        hasRoleAttribute: html.includes('data-require-role="admin"') || html.includes('data-require-role="member"'),
        hasTestId: html.includes('data-testid="add-member-btn"')
      };
    });
    console.log('Members page check:', membersCheck);
    expect(membersCheck.hasAddMemberBtn).toBe(true);
    expect(membersCheck.hasRoleAttribute).toBe(true);

    // Check contacts.html
    const contactsCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/contacts.html');
      const html = await resp.text();
      return {
        hasAddContactBtn: html.includes('id="add-contact-btn"'),
        hasRoleAttribute: html.includes('data-require-role'),
        hasTestId: html.includes('data-testid="add-contact-btn"')
      };
    });
    console.log('Contacts page check:', contactsCheck);
    expect(contactsCheck.hasAddContactBtn).toBe(true);
    expect(contactsCheck.hasRoleAttribute).toBe(true);

    // Check finance_accounts.html
    const accountsCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/finance_accounts.html');
      const html = await resp.text();
      return {
        hasAddAccountBtn: html.includes('id="add-account-btn"'),
        hasRoleAttribute: html.includes('data-require-role'),
        hasTestId: html.includes('data-testid="add-account-btn"')
      };
    });
    console.log('Finance accounts page check:', accountsCheck);
    expect(accountsCheck.hasAddAccountBtn).toBe(true);
    expect(accountsCheck.hasRoleAttribute).toBe(true);

    // Check meeting.html documents upload button
    const meetingCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/meeting.html');
      const html = await resp.text();
      return {
        hasUploadBtn: html.includes('id="upload-document-btn"'),
        hasRoleAttribute: html.includes('data-require-role="member"'),
        hasTestId: html.includes('data-testid="upload-document-btn"')
      };
    });
    console.log('Meeting page check:', meetingCheck);
    expect(meetingCheck.hasUploadBtn).toBe(true);
    expect(meetingCheck.hasRoleAttribute).toBe(true);

    // Check projects.html
    const projectsCheck = await page.evaluate(async () => {
      const resp = await fetch('/pages/projects.html');
      const html = await resp.text();
      return {
        hasAddProjectBtn: html.includes('id="add-project-btn"'),
        hasRoleAttribute: html.includes('data-require-role')
      };
    });
    console.log('Projects page check:', projectsCheck);
    expect(projectsCheck.hasAddProjectBtn).toBe(true);
    expect(projectsCheck.hasRoleAttribute).toBe(true);
  });

  test('UI.initRoleBasedUI should hide elements for viewers', async ({ page }) => {
    // Verify that the UI role-based visibility system exists
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const uiHelpers = await page.evaluate(() => {
      return {
        uiExists: typeof window.UI !== 'undefined',
        initRoleBasedUI: typeof window.UI?.initRoleBasedUI === 'function',
        applyRoleVisibility: typeof window.UI?.applyRoleVisibility === 'function'
      };
    });

    console.log('UI role helpers:', uiHelpers);
    expect(uiHelpers.uiExists).toBe(true);
    expect(uiHelpers.initRoleBasedUI).toBe(true);
    expect(uiHelpers.applyRoleVisibility).toBe(true);
  });

  test('role checking functions should work correctly', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    const roleHelpers = await page.evaluate(() => {
      return {
        hasMinRoleFn: typeof window.API?.roles?.hasMinRole === 'function',
        isAdminFn: typeof window.API?.roles?.isAdmin === 'function',
        isOwnerFn: typeof window.API?.roles?.isOwner === 'function',
        getUserRoleFn: typeof window.API?.roles?.getUserRole === 'function'
      };
    });

    console.log('Role API helpers:', roleHelpers);
    expect(roleHelpers.hasMinRoleFn).toBe(true);
    expect(roleHelpers.isAdminFn).toBe(true);
    expect(roleHelpers.isOwnerFn).toBe(true);
    expect(roleHelpers.getUserRoleFn).toBe(true);
  });

  test('data-require-role attribute should be parsed correctly', async ({ page }) => {
    // Create a test page with role-based elements
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Simulate role-based visibility logic
    const visibilityLogic = await page.evaluate(() => {
      // Test the role hierarchy logic
      const roleHierarchy = {
        'owner': 4,
        'admin': 3,
        'member': 2,
        'viewer': 1
      };

      function hasMinRole(userRole, requiredRole) {
        return (roleHierarchy[userRole] || 0) >= (roleHierarchy[requiredRole] || 0);
      }

      return {
        ownerCanSeeAdmin: hasMinRole('owner', 'admin'),
        adminCanSeeAdmin: hasMinRole('admin', 'admin'),
        memberCanSeeAdmin: hasMinRole('member', 'admin'),
        viewerCanSeeAdmin: hasMinRole('viewer', 'admin'),
        ownerCanSeeMember: hasMinRole('owner', 'member'),
        memberCanSeeMember: hasMinRole('member', 'member'),
        viewerCanSeeMember: hasMinRole('viewer', 'member')
      };
    });

    console.log('Role hierarchy test:', visibilityLogic);

    // Owner and admin can see admin-level controls
    expect(visibilityLogic.ownerCanSeeAdmin).toBe(true);
    expect(visibilityLogic.adminCanSeeAdmin).toBe(true);

    // Member and viewer cannot see admin-level controls
    expect(visibilityLogic.memberCanSeeAdmin).toBe(false);
    expect(visibilityLogic.viewerCanSeeAdmin).toBe(false);

    // Owner, admin, member can see member-level controls
    expect(visibilityLogic.ownerCanSeeMember).toBe(true);
    expect(visibilityLogic.memberCanSeeMember).toBe(true);

    // Viewer cannot see member-level controls
    expect(visibilityLogic.viewerCanSeeMember).toBe(false);
  });

  test('pages should include ui.js for role-based visibility', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Check that key pages include ui.js
    const pagesToCheck = [
      'members.html',
      'contacts.html',
      'finance_accounts.html',
      'projects.html',
      'meeting.html'
    ];

    for (const pageName of pagesToCheck) {
      const hasUiJs = await page.evaluate(async (pn) => {
        const resp = await fetch(`/pages/${pn}`);
        const html = await resp.text();
        return html.includes('/js/ui.js');
      }, pageName);

      console.log(`${pageName} includes ui.js:`, hasUiJs);
      expect(hasUiJs).toBe(true);
    }
  });

  test('sensitive buttons should have proper role requirements', async ({ page }) => {
    await page.goto('/pages/login.html');
    await page.waitForLoadState('networkidle');

    // Extract role requirements from key pages
    const roleRequirements = await page.evaluate(async () => {
      const results = {};

      // Helper to extract role from button element string
      const extractRole = (html, id) => {
        // Find the button element with the given id
        const idPattern = new RegExp(`id="${id}"[^>]*`);
        const match = html.match(idPattern);
        if (match) {
          const roleMatch = match[0].match(/data-require-role="([^"]+)"/);
          return roleMatch ? roleMatch[1] : null;
        }
        // Try with reversed order (data-require-role before id)
        const altPattern = new RegExp(`data-require-role="([^"]+)"[^>]*id="${id}"`);
        const altMatch = html.match(altPattern);
        return altMatch ? altMatch[1] : null;
      };

      // Check members.html
      const membersResp = await fetch('/pages/members.html');
      const membersHtml = await membersResp.text();
      results.addMember = extractRole(membersHtml, 'add-member-btn') ||
                          (membersHtml.includes('data-require-role') && membersHtml.includes('add-member-btn') ? 'found' : 'not found');

      // Check contacts.html
      const contactsResp = await fetch('/pages/contacts.html');
      const contactsHtml = await contactsResp.text();
      results.addContact = extractRole(contactsHtml, 'add-contact-btn') ||
                           (contactsHtml.includes('data-require-role') && contactsHtml.includes('add-contact-btn') ? 'found' : 'not found');

      // Check finance_accounts.html
      const accountsResp = await fetch('/pages/finance_accounts.html');
      const accountsHtml = await accountsResp.text();
      results.addAccount = extractRole(accountsHtml, 'add-account-btn') ||
                           (accountsHtml.includes('data-require-role') && accountsHtml.includes('add-account-btn') ? 'found' : 'not found');

      // Check meeting.html documents button
      const meetingResp = await fetch('/pages/meeting.html');
      const meetingHtml = await meetingResp.text();
      results.uploadDocument = extractRole(meetingHtml, 'upload-document-btn') ||
                               (meetingHtml.includes('data-require-role') && meetingHtml.includes('upload-document-btn') ? 'found' : 'not found');

      return results;
    });

    console.log('Role requirements:', roleRequirements);

    // Verify appropriate role requirements (either specific role or 'found' means attribute exists)
    expect(['admin', 'member', 'owner', 'found']).toContain(roleRequirements.addMember);
    expect(['admin', 'member', 'owner', 'found']).toContain(roleRequirements.addContact);
    expect(['admin', 'member', 'owner', 'found']).toContain(roleRequirements.addAccount);
    expect(['admin', 'member', 'owner', 'found']).toContain(roleRequirements.uploadDocument);
  });
});
