/// <reference path="../pb_data/types.d.ts" />

/**
 * Migration: User Profile & Preferences
 * Adds profile and preference fields to the users collection for account management.
 * Updated for PocketBase v0.23+ API - uses fields.add() with specific Field classes
 *
 * New fields:
 * - display_name (text, optional) - User's preferred display name
 * - timezone (text, optional) - User's timezone (e.g., "America/Chicago")
 * - notify_meeting_invites (bool, default true) - Email notifications for meeting invitations
 * - notify_meeting_reminders (bool, default true) - Email notifications for meeting reminders
 * - default_org (relation to organizations, optional) - User's default organization
 */

migrate((app) => {
    console.log("[User Profile] Adding profile fields to users collection...");

    const users = app.findCollectionByNameOrId("users");
    if (!users) {
        console.log("[User Profile] Users collection not found, skipping migration");
        return;
    }

    // Get organizations collection ID for the relation field
    let organizationsId = null;
    try {
        const orgs = app.findCollectionByNameOrId("organizations");
        if (orgs) {
            organizationsId = orgs.id;
        }
    } catch (e) {
        console.log("[User Profile] Organizations collection not found, default_org field will be skipped");
    }

    // Check if fields already exist
    const existingFieldNames = [];
    for (let i = 0; i < users.fields.length; i++) {
        existingFieldNames.push(users.fields[i].name);
    }

    // Add display_name field
    if (!existingFieldNames.includes("display_name")) {
        users.fields.add(new TextField({
            name: "display_name",
            required: false,
            max: 200,
            hidden: false,
            presentable: false
        }));
        console.log("[User Profile] Added display_name field");
    }

    // Add timezone field
    if (!existingFieldNames.includes("timezone")) {
        users.fields.add(new TextField({
            name: "timezone",
            required: false,
            max: 100,
            hidden: false,
            presentable: false
        }));
        console.log("[User Profile] Added timezone field");
    }

    // Add notify_meeting_invites field
    if (!existingFieldNames.includes("notify_meeting_invites")) {
        users.fields.add(new BoolField({
            name: "notify_meeting_invites",
            required: false,
            hidden: false,
            presentable: false
        }));
        console.log("[User Profile] Added notify_meeting_invites field");
    }

    // Add notify_meeting_reminders field
    if (!existingFieldNames.includes("notify_meeting_reminders")) {
        users.fields.add(new BoolField({
            name: "notify_meeting_reminders",
            required: false,
            hidden: false,
            presentable: false
        }));
        console.log("[User Profile] Added notify_meeting_reminders field");
    }

    // Add default_org relation field if organizations collection exists
    if (organizationsId && !existingFieldNames.includes("default_org")) {
        users.fields.add(new RelationField({
            name: "default_org",
            required: false,
            collectionId: organizationsId,
            cascadeDelete: false,
            maxSelect: 1,
            hidden: false,
            presentable: false
        }));
        console.log("[User Profile] Added default_org field");
    }

    // Save the updated collection
    app.save(users);

    console.log("[User Profile] User profile fields added successfully!");

}, (app) => {
    // Rollback: remove the added fields
    console.log("[User Profile] Rolling back user profile fields...");

    const users = app.findCollectionByNameOrId("users");
    if (!users) return;

    const fieldsToRemove = ["display_name", "timezone", "notify_meeting_invites", "notify_meeting_reminders", "default_org"];

    for (const fieldName of fieldsToRemove) {
        users.fields.removeByName(fieldName);
    }

    app.save(users);
    console.log("[User Profile] Rollback complete");
});
