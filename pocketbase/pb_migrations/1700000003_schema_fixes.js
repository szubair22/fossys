/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Schema Fixes
 * Updated for PocketBase v0.23+ API - flat field structure
 *
 * Note: In PocketBase v0.23+, fields.push() doesn't work.
 * The attendance_status field has been moved to the participants collection definition
 * in the init_schema migration. The "annual" meeting type has also been added there.
 * This migration is now a no-op but kept for compatibility.
 */

migrate((app) => {
  // All schema fixes have been incorporated into 1700000000_init_schema.js:
  // - attendance_status field added to participants collection
  // - "annual" added to meetings.meeting_type values
  // - "annual" added to meeting_templates.default_meeting_type values

  // This migration intentionally does nothing as the fixes are in the init schema.
  // It's kept for backwards compatibility with existing deployment scripts.

}, (app) => {
  // Rollback - backward compatible, no action needed
});
