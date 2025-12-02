/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Allow organization admins to delete organizations
 * Updates the delete rule to allow both owners and admins from org_memberships
 */

migrate((app) => {
  const organizations = app.findCollectionByNameOrId("organizations");

  // Update delete rule to allow owner OR admin members
  // The owner check is direct, admin check uses org_memberships collection
  organizations.deleteRule = "@request.auth.id = owner.id || (@request.auth.id != '' && @collection.org_memberships.organization = id && @collection.org_memberships.user = @request.auth.id && @collection.org_memberships.role = 'admin' && @collection.org_memberships.is_active = true)";

  app.save(organizations);

}, (app) => {
  // Rollback - restore original delete rule (owner only)
  const organizations = app.findCollectionByNameOrId("organizations");
  organizations.deleteRule = "@request.auth.id = owner.id";
  app.save(organizations);
});
