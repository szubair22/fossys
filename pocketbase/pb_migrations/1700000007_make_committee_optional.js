/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Make committee field optional in meetings
 *
 * The meetings collection was created with committee as required,
 * but the UI allows creating standalone meetings without a committee.
 * This migration makes the committee field optional.
 */

migrate((app) => {
  const meetings = app.findCollectionByNameOrId("meetings");

  if (!meetings) {
    console.log("Meetings collection not found, skipping migration");
    return;
  }

  // Find the committee field and make it optional
  const committeeField = meetings.fields.find(f => f.name === "committee");
  if (committeeField) {
    committeeField.required = false;
    app.save(meetings);
    console.log("Made committee field optional in meetings collection");
  }

}, (app) => {
  // Rollback: make committee required again
  const meetings = app.findCollectionByNameOrId("meetings");

  if (!meetings) return;

  const committeeField = meetings.fields.find(f => f.name === "committee");
  if (committeeField) {
    committeeField.required = true;
    app.save(meetings);
  }
});
