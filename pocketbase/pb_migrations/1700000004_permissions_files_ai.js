/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Permissions, Files, AI Integrations, and Recordings
 * Updated for PocketBase v0.23+ API - flat field structure
 *
 * Important: In v0.23+, we must use collection.id from findCollectionByNameOrId()
 * instead of collection names as strings for collectionId in relation fields.
 *
 * Note: The organization plan fields (plan, features, max_members, storage_used_bytes)
 * have been moved to the init_schema migration to avoid fields.push() issues.
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

  const agendaItemsCollection = app.findCollectionByNameOrId("agenda_items");
  const agendaItemsId = agendaItemsCollection.id;

  const motionsCollection = app.findCollectionByNameOrId("motions");
  const motionsId = motionsCollection.id;

  // ========================================
  // NEW: Organization Memberships collection
  // ========================================
  const orgMemberships = new Collection({
    name: "org_memberships",
    type: "base",
    system: false,
    fields: [
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: organizationsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "role",
        type: "select",
        required: true,
        values: ["owner", "admin", "member", "viewer"]
      },
      {
        name: "is_active",
        type: "bool",
        required: false
      },
      {
        name: "invited_by",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "invited_at",
        type: "date",
        required: false
      },
      {
        name: "joined_at",
        type: "date",
        required: false
      },
      {
        name: "permissions",
        type: "json",
        required: false
      }
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_org_memberships_unique ON org_memberships (organization, user)",
      "CREATE INDEX idx_org_memberships_org ON org_memberships (organization)",
      "CREATE INDEX idx_org_memberships_user ON org_memberships (user)",
      "CREATE INDEX idx_org_memberships_role ON org_memberships (role)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(orgMemberships);

  orgMemberships.listRule = "@request.auth.id != '' && (user.id = @request.auth.id || organization.owner.id = @request.auth.id)";
  orgMemberships.viewRule = "@request.auth.id != '' && (user.id = @request.auth.id || organization.owner.id = @request.auth.id)";
  orgMemberships.createRule = "@request.auth.id = organization.owner.id";
  orgMemberships.updateRule = "@request.auth.id = organization.owner.id";
  orgMemberships.deleteRule = "@request.auth.id = organization.owner.id";
  app.save(orgMemberships);

  // ========================================
  // NEW: Files collection
  // ========================================
  const files = new Collection({
    name: "files",
    type: "base",
    system: false,
    fields: [
      {
        name: "file",
        type: "file",
        required: true,
        maxSelect: 1,
        maxSize: 52428800,
        mimeTypes: [
          "application/pdf",
          "application/msword",
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "application/vnd.ms-excel",
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "application/vnd.ms-powerpoint",
          "application/vnd.openxmlformats-officedocument.presentationml.presentation",
          "text/plain",
          "text/csv",
          "image/png",
          "image/jpeg",
          "image/gif",
          "image/webp"
        ]
      },
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: organizationsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "meeting",
        type: "relation",
        required: false,
        collectionId: meetingsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "agenda_item",
        type: "relation",
        required: false,
        collectionId: agendaItemsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "motion",
        type: "relation",
        required: false,
        collectionId: motionsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "name",
        type: "text",
        required: true,
        min: 1,
        max: 255
      },
      {
        name: "description",
        type: "text",
        required: false,
        max: 1000
      },
      {
        name: "file_type",
        type: "select",
        required: false,
        values: ["document", "spreadsheet", "presentation", "image", "other"]
      },
      {
        name: "file_size",
        type: "number",
        required: false,
        min: 0
      },
      {
        name: "uploaded_by",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      }
    ],
    indexes: [
      "CREATE INDEX idx_files_org ON files (organization)",
      "CREATE INDEX idx_files_meeting ON files (meeting)",
      "CREATE INDEX idx_files_agenda_item ON files (agenda_item)",
      "CREATE INDEX idx_files_motion ON files (motion)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(files);

  files.listRule = "@request.auth.id != ''";
  files.viewRule = "@request.auth.id != ''";
  files.createRule = "@request.auth.id != ''";
  files.updateRule = "@request.auth.id = uploaded_by.id || @request.auth.id = organization.owner.id";
  files.deleteRule = "@request.auth.id = uploaded_by.id || @request.auth.id = organization.owner.id";
  app.save(files);

  // ========================================
  // NEW: AI Integrations collection
  // ========================================
  const aiIntegrations = new Collection({
    name: "ai_integrations",
    type: "base",
    system: false,
    fields: [
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: organizationsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "provider",
        type: "select",
        required: true,
        values: ["openai", "anthropic", "google", "custom"]
      },
      {
        name: "api_key",
        type: "text",
        required: true,
        min: 10,
        max: 500
      },
      {
        name: "model",
        type: "text",
        required: false,
        max: 100
      },
      {
        name: "is_active",
        type: "bool",
        required: false
      },
      {
        name: "settings",
        type: "json",
        required: false
      },
      {
        name: "created_by",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "last_used_at",
        type: "date",
        required: false
      },
      {
        name: "usage_count",
        type: "number",
        required: false,
        min: 0
      }
    ],
    indexes: [
      "CREATE INDEX idx_ai_integrations_org ON ai_integrations (organization)",
      "CREATE INDEX idx_ai_integrations_provider ON ai_integrations (provider)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(aiIntegrations);

  aiIntegrations.listRule = "@request.auth.id = organization.owner.id";
  aiIntegrations.viewRule = "@request.auth.id = organization.owner.id";
  aiIntegrations.createRule = "@request.auth.id = organization.owner.id";
  aiIntegrations.updateRule = "@request.auth.id = organization.owner.id";
  aiIntegrations.deleteRule = "@request.auth.id = organization.owner.id";
  app.save(aiIntegrations);

  // ========================================
  // NEW: Recordings collection
  // ========================================
  const recordings = new Collection({
    name: "recordings",
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
        name: "title",
        type: "text",
        required: true,
        min: 1,
        max: 300
      },
      {
        name: "description",
        type: "text",
        required: false,
        max: 1000
      },
      {
        name: "provider",
        type: "select",
        required: false,
        values: ["jitsi", "zoom", "local", "youtube", "vimeo", "other"]
      },
      {
        name: "url",
        type: "url",
        required: false
      },
      {
        name: "file",
        type: "file",
        required: false,
        maxSelect: 1,
        maxSize: 5368709120,
        mimeTypes: ["video/mp4", "video/webm", "video/quicktime", "audio/mpeg", "audio/wav", "audio/ogg"]
      },
      {
        name: "thumbnail",
        type: "file",
        required: false,
        maxSelect: 1,
        maxSize: 5242880,
        mimeTypes: ["image/png", "image/jpeg", "image/webp"]
      },
      {
        name: "recording_date",
        type: "date",
        required: false
      },
      {
        name: "duration_seconds",
        type: "number",
        required: false,
        min: 0
      },
      {
        name: "file_size",
        type: "number",
        required: false,
        min: 0
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["processing", "ready", "failed", "archived"]
      },
      {
        name: "visibility",
        type: "select",
        required: false,
        values: ["private", "members", "public"]
      },
      {
        name: "created_by",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      }
    ],
    indexes: [
      "CREATE INDEX idx_recordings_meeting ON recordings (meeting)",
      "CREATE INDEX idx_recordings_status ON recordings (status)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(recordings);

  recordings.listRule = "@request.auth.id != ''";
  recordings.viewRule = "@request.auth.id != ''";
  recordings.createRule = "@request.auth.id != ''";
  recordings.updateRule = "@request.auth.id = created_by.id || @request.auth.id = meeting.created_by.id";
  recordings.deleteRule = "@request.auth.id = created_by.id || @request.auth.id = meeting.created_by.id";
  app.save(recordings);

  // Note: Field additions to meeting_notifications and organizations are skipped
  // due to fields.push() limitation in PocketBase v0.23+.
  // Email fields have been added to meeting_notifications in migration 1.
  // Organization plan fields can be added via admin UI or raw SQL.

}, (app) => {
  try { app.delete(app.findCollectionByNameOrId("recordings")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("ai_integrations")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("files")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("org_memberships")); } catch(e) {}
});
