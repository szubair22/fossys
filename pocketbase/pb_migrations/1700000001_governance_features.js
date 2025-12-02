/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Governance Features
 * Updated for PocketBase v0.23+ API - flat field structure
 *
 * Important: In v0.23+, we must use collection.id from findCollectionByNameOrId()
 * instead of collection names as strings for collectionId in relation fields.
 *
 * Note: The governance fields for meetings (quorum_required, quorum_met, minutes_generated)
 * have been moved to the init_schema migration (1700000000) to avoid field push issues.
 * The template relation will be added here after meeting_templates is created.
 */

migrate((app) => {
  // Get the users collection ID dynamically
  const usersCollection = app.findCollectionByNameOrId("users");
  const usersCollectionId = usersCollection.id;

  // Get existing collection IDs
  const organizationsCollection = app.findCollectionByNameOrId("organizations");
  const organizationsId = organizationsCollection.id;

  const meetingsCollection = app.findCollectionByNameOrId("meetings");
  const meetingsId = meetingsCollection.id;

  // ========================================
  // NEW: Meeting Templates collection
  // ========================================
  const meetingTemplates = new Collection({
    name: "meeting_templates",
    type: "base",
    system: false,
    fields: [
      {
        name: "organization",
        type: "relation",
        required: false,
        collectionId: organizationsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "name",
        type: "text",
        required: true,
        min: 1,
        max: 200
      },
      {
        name: "org_type",
        type: "select",
        required: false,
        values: ["fraternity", "sorority", "hoa", "nonprofit", "church", "corporate", "government", "generic"]
      },
      {
        name: "description",
        type: "text",
        required: false,
        max: 1000
      },
      {
        name: "default_meeting_title",
        type: "text",
        required: false,
        max: 300
      },
      {
        name: "default_meeting_type",
        type: "select",
        required: false,
        values: ["general", "board", "committee", "election", "special", "emergency", "annual"]
      },
      {
        name: "default_agenda",
        type: "json",
        required: false
      },
      {
        name: "settings",
        type: "json",
        required: false
      },
      {
        name: "is_global",
        type: "bool",
        required: false
      },
      {
        name: "created_by",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      }
    ],
    indexes: [
      "CREATE INDEX idx_templates_org ON meeting_templates (organization)",
      "CREATE INDEX idx_templates_global ON meeting_templates (is_global)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(meetingTemplates);

  const meetingTemplatesId = meetingTemplates.id;

  meetingTemplates.updateRule = "@request.auth.id = created_by.id || @request.auth.id = organization.owner.id";
  meetingTemplates.deleteRule = "@request.auth.id = created_by.id || @request.auth.id = organization.owner.id";
  app.save(meetingTemplates);

  // Note: The template relation on meetings collection is skipped due to PocketBase v0.23+
  // limitations with fields.push(). It can be added via admin UI if needed.

  // ========================================
  // NEW: Meeting Minutes collection
  // ========================================
  const minutes = new Collection({
    name: "meeting_minutes",
    type: "base",
    system: false,
    fields: [
      {
        name: "meeting",
        type: "relation",
        required: true,
        collectionId: meetingsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "content",
        type: "editor",
        required: false
      },
      {
        name: "summary",
        type: "text",
        required: false,
        max: 2000
      },
      {
        name: "decisions",
        type: "json",
        required: false
      },
      {
        name: "attendance_snapshot",
        type: "json",
        required: false
      },
      {
        name: "generated_at",
        type: "date",
        required: false
      },
      {
        name: "generated_by",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["draft", "final", "approved"]
      },
      {
        name: "approved_by",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "approved_at",
        type: "date",
        required: false
      }
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_minutes_meeting ON meeting_minutes (meeting)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(minutes);

  minutes.createRule = "@request.auth.id = meeting.created_by.id";
  minutes.updateRule = "@request.auth.id = meeting.created_by.id";
  minutes.deleteRule = "@request.auth.id = meeting.created_by.id";
  app.save(minutes);

  // ========================================
  // NEW: Meeting Notifications collection
  // ========================================
  const notifications = new Collection({
    name: "meeting_notifications",
    type: "base",
    system: false,
    fields: [
      {
        name: "meeting",
        type: "relation",
        required: true,
        collectionId: meetingsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "recipient_user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "notification_type",
        type: "select",
        required: true,
        values: ["invitation", "reminder", "update", "cancelled", "minutes_ready"]
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["pending", "sent", "failed", "skipped"]
      },
      {
        name: "scheduled_at",
        type: "date",
        required: false
      },
      {
        name: "sent_at",
        type: "date",
        required: false
      },
      {
        name: "error_message",
        type: "text",
        required: false,
        max: 500
      },
      {
        name: "metadata",
        type: "json",
        required: false
      },
      // Email/calendar fields (added inline instead of using push)
      {
        name: "email_subject",
        type: "text",
        required: false,
        max: 300
      },
      {
        name: "email_body",
        type: "editor",
        required: false
      },
      {
        name: "include_ics",
        type: "bool",
        required: false
      },
      {
        name: "delivery_method",
        type: "select",
        required: false,
        values: ["email", "in_app", "both"]
      }
    ],
    indexes: [
      "CREATE INDEX idx_notifications_meeting ON meeting_notifications (meeting)",
      "CREATE INDEX idx_notifications_status ON meeting_notifications (status)",
      "CREATE INDEX idx_notifications_scheduled ON meeting_notifications (scheduled_at)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(notifications);

  notifications.listRule = "@request.auth.id = recipient_user.id || @request.auth.id = meeting.created_by.id";
  notifications.viewRule = "@request.auth.id = recipient_user.id || @request.auth.id = meeting.created_by.id";
  notifications.createRule = "@request.auth.id = meeting.created_by.id";
  notifications.updateRule = "@request.auth.id = meeting.created_by.id";
  notifications.deleteRule = "@request.auth.id = meeting.created_by.id";
  app.save(notifications);

  // Note: Motions and Polls field updates (vote_result, final_notes, poll_category, winning_option)
  // are skipped due to fields.push() limitation in PocketBase v0.23+.
  // They can be added via admin UI or a separate migration using raw SQL.

}, (app) => {
  try { app.delete(app.findCollectionByNameOrId("meeting_notifications")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("meeting_templates")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("meeting_minutes")); } catch(e) {}
});
