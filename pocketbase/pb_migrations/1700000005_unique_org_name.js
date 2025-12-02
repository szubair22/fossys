/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Add unique constraint on organization names
 * Ensures organization names are unique in the database
 */

migrate((app) => {
  const organizations = app.findCollectionByNameOrId("organizations");

  // Add unique index on organization name
  organizations.indexes = [
    "CREATE UNIQUE INDEX idx_organizations_name ON organizations (name)"
  ];

  app.save(organizations);

}, (app) => {
  // Rollback - remove the unique index
  const organizations = app.findCollectionByNameOrId("organizations");
  organizations.indexes = [];
  app.save(organizations);
});
