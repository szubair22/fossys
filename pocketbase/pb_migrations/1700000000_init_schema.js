/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: Initial Schema
 * Creates all core collections for OrgMeet
 * Updated for PocketBase v0.23+ API
 *
 * Important: In v0.23+, we can't use collection names as collectionId in relation fields.
 * We must use the actual collection ID, which is auto-generated.
 * To reference collections created in this migration, we save them first, then use their .id property.
 */

migrate((app) => {
  // Get the users collection ID dynamically
  const usersCollection = app.findCollectionByNameOrId("users");
  const usersCollectionId = usersCollection.id;

  // ========================================
  // Organizations collection
  // ========================================
  const organizations = new Collection({
    name: "organizations",
    type: "base",
    system: false,
    fields: [
      {
        name: "name",
        type: "text",
        required: true,
        min: 1,
        max: 200
      },
      {
        name: "description",
        type: "text",
        required: false,
        max: 2000
      },
      {
        name: "logo",
        type: "file",
        required: false,
        maxSelect: 1,
        maxSize: 5242880,
        mimeTypes: ["image/png", "image/jpeg", "image/svg+xml"]
      },
      {
        name: "settings",
        type: "json",
        required: false
      },
      {
        name: "owner",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      }
    ],
    indexes: [],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(organizations);

  // Capture the auto-generated ID for use in other collections
  const organizationsId = organizations.id;

  // Update organization rules now that the field exists
  organizations.updateRule = "@request.auth.id = owner.id";
  organizations.deleteRule = "@request.auth.id = owner.id";
  app.save(organizations);

  // ========================================
  // Committees collection
  // ========================================
  const committees = new Collection({
    name: "committees",
    type: "base",
    system: false,
    fields: [
      {
        name: "organization",
        type: "relation",
        required: true,
        collectionId: organizationsId, // Use the auto-generated ID
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
        name: "description",
        type: "text",
        required: false,
        max: 2000
      },
      {
        name: "admins",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 100
      }
    ],
    indexes: [],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(committees);

  const committeesId = committees.id;

  // Update committee rules
  committees.createRule = "@request.auth.id != '' && @request.auth.id = organization.owner.id";
  committees.updateRule = "@request.auth.id != '' && (@request.auth.id = organization.owner.id || @request.auth.id ?= admins.id)";
  committees.deleteRule = "@request.auth.id = organization.owner.id";
  app.save(committees);

  // ========================================
  // Meetings collection
  // ========================================
  const meetings = new Collection({
    name: "meetings",
    type: "base",
    system: false,
    fields: [
      {
        name: "committee",
        type: "relation",
        required: true,
        collectionId: committeesId,
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
        type: "editor",
        required: false
      },
      {
        name: "start_time",
        type: "date",
        required: true
      },
      {
        name: "end_time",
        type: "date",
        required: false
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["draft", "scheduled", "in_progress", "completed", "cancelled"]
      },
      {
        name: "jitsi_room",
        type: "text",
        required: false,
        max: 100
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
        name: "meeting_type",
        type: "select",
        required: false,
        values: ["general", "board", "committee", "election", "special", "emergency", "annual"]
      },
      {
        name: "quorum_required",
        type: "number",
        required: false,
        min: 0,
        max: 1000
      },
      {
        name: "quorum_met",
        type: "bool",
        required: false
      },
      {
        name: "minutes_generated",
        type: "bool",
        required: false
      }
    ],
    indexes: [
      "CREATE INDEX idx_meetings_status ON meetings (status)",
      "CREATE INDEX idx_meetings_start_time ON meetings (start_time)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(meetings);

  const meetingsId = meetings.id;

  // Update meeting rules
  meetings.updateRule = "@request.auth.id = created_by.id || @request.auth.id ?= committee.admins.id";
  meetings.deleteRule = "@request.auth.id = created_by.id || @request.auth.id ?= committee.admins.id";
  app.save(meetings);

  // ========================================
  // Participants collection
  // ========================================
  const participants = new Collection({
    name: "participants",
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
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "role",
        type: "select",
        required: true,
        values: ["admin", "moderator", "member", "guest", "observer"]
      },
      {
        name: "is_present",
        type: "bool",
        required: false
      },
      {
        name: "can_vote",
        type: "bool",
        required: false
      },
      {
        name: "vote_weight",
        type: "number",
        required: false,
        min: 0,
        max: 100
      },
      {
        name: "joined_at",
        type: "date",
        required: false
      },
      {
        name: "left_at",
        type: "date",
        required: false
      },
      {
        name: "attendance_status",
        type: "select",
        required: false,
        values: ["invited", "present", "absent", "excused"]
      }
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_participants_unique ON participants (meeting, user)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(participants);

  // Update participant rules
  participants.updateRule = "@request.auth.id = user.id || @request.auth.id = meeting.created_by.id";
  participants.deleteRule = "@request.auth.id = meeting.created_by.id";
  app.save(participants);

  // ========================================
  // Agenda Items collection - created without self-reference first
  // ========================================
  const agendaItems = new Collection({
    name: "agenda_items",
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
        type: "editor",
        required: false
      },
      {
        name: "order",
        type: "number",
        required: true,
        min: 0
      },
      {
        name: "duration_minutes",
        type: "number",
        required: false,
        min: 0,
        max: 480
      },
      {
        name: "item_type",
        type: "select",
        required: true,
        values: ["topic", "motion", "election", "break", "other"]
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["pending", "in_progress", "completed", "skipped"]
      }
    ],
    indexes: [
      "CREATE INDEX idx_agenda_items_order ON agenda_items (meeting, \"order\")"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(agendaItems);

  const agendaItemsId = agendaItems.id;

  // Update agenda item rules
  agendaItems.updateRule = "@request.auth.id = meeting.created_by.id";
  agendaItems.deleteRule = "@request.auth.id = meeting.created_by.id";
  app.save(agendaItems);

  // Note: Self-referencing parent_item field can be added via admin UI or a later migration

  // ========================================
  // Motions collection
  // ========================================
  const motions = new Collection({
    name: "motions",
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
        name: "agenda_item",
        type: "relation",
        required: false,
        collectionId: agendaItemsId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "number",
        type: "text",
        required: false,
        max: 50
      },
      {
        name: "title",
        type: "text",
        required: true,
        min: 1,
        max: 500
      },
      {
        name: "text",
        type: "editor",
        required: true
      },
      {
        name: "reason",
        type: "editor",
        required: false
      },
      {
        name: "submitter",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "supporters",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 100
      },
      {
        name: "workflow_state",
        type: "select",
        required: true,
        values: ["draft", "submitted", "screening", "discussion", "voting", "accepted", "rejected", "withdrawn", "referred"]
      },
      {
        name: "category",
        type: "text",
        required: false,
        max: 100
      },
      {
        name: "attachments",
        type: "file",
        required: false,
        maxSelect: 10,
        maxSize: 10485760
      }
    ],
    indexes: [
      "CREATE INDEX idx_motions_state ON motions (workflow_state)",
      "CREATE INDEX idx_motions_meeting ON motions (meeting)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(motions);

  const motionsId = motions.id;

  // Update motion rules
  motions.updateRule = "@request.auth.id = submitter.id || @request.auth.id = meeting.created_by.id";
  motions.deleteRule = "@request.auth.id = submitter.id || @request.auth.id = meeting.created_by.id";
  app.save(motions);

  // ========================================
  // Polls collection
  // ========================================
  const polls = new Collection({
    name: "polls",
    type: "base",
    system: false,
    fields: [
      {
        name: "motion",
        type: "relation",
        required: false,
        collectionId: motionsId,
        cascadeDelete: true,
        maxSelect: 1
      },
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
        name: "poll_type",
        type: "select",
        required: true,
        values: ["yes_no", "yes_no_abstain", "multiple_choice", "ranked_choice"]
      },
      {
        name: "options",
        type: "json",
        required: false
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["draft", "open", "closed", "published"]
      },
      {
        name: "results",
        type: "json",
        required: false
      },
      {
        name: "anonymous",
        type: "bool",
        required: false
      },
      {
        name: "opened_at",
        type: "date",
        required: false
      },
      {
        name: "closed_at",
        type: "date",
        required: false
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
      "CREATE INDEX idx_polls_status ON polls (status)",
      "CREATE INDEX idx_polls_meeting ON polls (meeting)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(polls);

  const pollsId = polls.id;

  // Update poll rules
  polls.updateRule = "@request.auth.id = created_by.id || @request.auth.id = meeting.created_by.id";
  polls.deleteRule = "@request.auth.id = created_by.id || @request.auth.id = meeting.created_by.id";
  app.save(polls);

  // ========================================
  // Votes collection
  // ========================================
  const votes = new Collection({
    name: "votes",
    type: "base",
    system: false,
    fields: [
      {
        name: "poll",
        type: "relation",
        required: true,
        collectionId: pollsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "value",
        type: "json",
        required: true
      },
      {
        name: "weight",
        type: "number",
        required: false,
        min: 0,
        max: 100
      },
      {
        name: "delegated_from",
        type: "relation",
        required: false,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      }
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_votes_unique ON votes (poll, user)"
    ],
    listRule: null,
    viewRule: null,
    createRule: null,
    updateRule: null,
    deleteRule: null
  });
  app.save(votes);

  // Update vote rules
  votes.listRule = "@request.auth.id = user.id || poll.anonymous = false";
  votes.viewRule = "@request.auth.id = user.id || poll.anonymous = false";
  votes.createRule = "@request.auth.id != '' && poll.status = 'open'";
  app.save(votes);

  // ========================================
  // Speaker Queue collection
  // ========================================
  const speakerQueue = new Collection({
    name: "speaker_queue",
    type: "base",
    system: false,
    fields: [
      {
        name: "agenda_item",
        type: "relation",
        required: true,
        collectionId: agendaItemsId,
        cascadeDelete: true,
        maxSelect: 1
      },
      {
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "position",
        type: "number",
        required: true,
        min: 0
      },
      {
        name: "status",
        type: "select",
        required: true,
        values: ["waiting", "speaking", "finished", "cancelled"]
      },
      {
        name: "speaker_type",
        type: "select",
        required: true,
        values: ["normal", "point_of_order", "reply"]
      },
      {
        name: "speaking_time_seconds",
        type: "number",
        required: false,
        min: 0
      },
      {
        name: "started_at",
        type: "date",
        required: false
      },
      {
        name: "ended_at",
        type: "date",
        required: false
      }
    ],
    indexes: [
      "CREATE INDEX idx_speaker_queue_position ON speaker_queue (agenda_item, position)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(speakerQueue);

  // Update speaker queue rules
  speakerQueue.updateRule = "@request.auth.id = user.id || @request.auth.id = agenda_item.meeting.created_by.id";
  speakerQueue.deleteRule = "@request.auth.id = user.id || @request.auth.id = agenda_item.meeting.created_by.id";
  app.save(speakerQueue);

  // ========================================
  // Chat Messages collection
  // ========================================
  const chatMessages = new Collection({
    name: "chat_messages",
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
        name: "user",
        type: "relation",
        required: true,
        collectionId: usersCollectionId,
        cascadeDelete: false,
        maxSelect: 1
      },
      {
        name: "message",
        type: "text",
        required: true,
        min: 1,
        max: 5000
      },
      {
        name: "message_type",
        type: "select",
        required: true,
        values: ["text", "system", "announcement"]
      }
    ],
    indexes: [
      "CREATE INDEX idx_chat_messages_meeting ON chat_messages (meeting)"
    ],
    listRule: "@request.auth.id != ''",
    viewRule: "@request.auth.id != ''",
    createRule: "@request.auth.id != ''",
    updateRule: null,
    deleteRule: null
  });
  app.save(chatMessages);

  // Update chat message rules
  chatMessages.deleteRule = "@request.auth.id = meeting.created_by.id";
  app.save(chatMessages);

}, (app) => {
  // Rollback
  try { app.delete(app.findCollectionByNameOrId("chat_messages")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("speaker_queue")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("votes")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("polls")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("motions")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("agenda_items")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("participants")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("meetings")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("committees")); } catch(e) {}
  try { app.delete(app.findCollectionByNameOrId("organizations")); } catch(e) {}
});
