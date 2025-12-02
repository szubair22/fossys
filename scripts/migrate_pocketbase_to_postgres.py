#!/usr/bin/env python3
"""
PocketBase (SQLite) to PostgreSQL Migration Script

This script migrates all data from the PocketBase SQLite database
to the new PostgreSQL database used by the FastAPI backend.

Usage:
    python migrate_pocketbase_to_postgres.py [--pb-path PATH] [--pg-url URL]

Arguments:
    --pb-path: Path to PocketBase data.db (default: ./pocketbase/pb_data/data.db)
    --pg-url: PostgreSQL connection URL (default: from environment)
"""

import argparse
import sqlite3
import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional

# PostgreSQL connection
import psycopg2
from psycopg2.extras import execute_values


# Mapping of PocketBase collection names to PostgreSQL table names
COLLECTION_TO_TABLE = {
    "users": "users",
    "organizations": "organizations",
    "org_memberships": "org_memberships",
    "committees": "committees",
    "meetings": "meetings",
    "participants": "participants",
    "agenda_items": "agenda_items",
    "motions": "motions",
    "polls": "polls",
    "votes": "votes",
    "speaker_queue": "speaker_queue",
    "chat_messages": "chat_messages",
    "meeting_templates": "meeting_templates",
    "meeting_minutes": "meeting_minutes",
    "meeting_notifications": "meeting_notifications",
    "files": "files",
    "ai_integrations": "ai_integrations",
    "recordings": "recordings",
}

# Column mappings for each collection (PocketBase column -> PostgreSQL column)
# None means same name, dict means rename or transform
COLUMN_MAPPINGS = {
    "users": {
        "id": "id",
        "email": "email",
        "passwordHash": "password_hash",
        "name": "name",
        "verified": "verified",
        "display_name": "display_name",
        "timezone": "timezone",
        "notify_meeting_invites": "notify_meeting_invites",
        "notify_meeting_reminders": "notify_meeting_reminders",
        "default_org": "default_org_id",
        "avatar": "avatar",
        "created": "created",
        "updated": "updated",
    },
    "organizations": {
        "id": "id",
        "name": "name",
        "description": "description",
        "logo": "logo",
        "settings": "settings",
        "owner": "owner_id",
        "created": "created",
        "updated": "updated",
    },
    "org_memberships": {
        "id": "id",
        "organization": "organization_id",
        "user": "user_id",
        "role": "role",
        "is_active": "is_active",
        "invited_by": "invited_by_id",
        "invited_at": "invited_at",
        "joined_at": "joined_at",
        "permissions": "permissions",
        "created": "created",
        "updated": "updated",
    },
    "committees": {
        "id": "id",
        "organization": "organization_id",
        "name": "name",
        "description": "description",
        "created": "created",
        "updated": "updated",
    },
    "meetings": {
        "id": "id",
        "committee": "committee_id",
        "title": "title",
        "description": "description",
        "start_time": "start_time",
        "end_time": "end_time",
        "status": "status",
        "jitsi_room": "jitsi_room",
        "settings": "settings",
        "created_by": "created_by_id",
        "meeting_type": "meeting_type",
        "quorum_required": "quorum_required",
        "quorum_met": "quorum_met",
        "minutes_generated": "minutes_generated",
        "created": "created",
        "updated": "updated",
    },
    "participants": {
        "id": "id",
        "meeting": "meeting_id",
        "user": "user_id",
        "role": "role",
        "is_present": "is_present",
        "attendance_status": "attendance_status",
        "can_vote": "can_vote",
        "vote_weight": "vote_weight",
        "joined_at": "joined_at",
        "left_at": "left_at",
        "created": "created",
        "updated": "updated",
    },
    "agenda_items": {
        "id": "id",
        "meeting": "meeting_id",
        "title": "title",
        "description": "description",
        "order": "order",
        "duration_minutes": "duration_minutes",
        "item_type": "item_type",
        "status": "status",
        "created": "created",
        "updated": "updated",
    },
    "motions": {
        "id": "id",
        "meeting": "meeting_id",
        "agenda_item": "agenda_item_id",
        "number": "number",
        "title": "title",
        "text": "text",
        "reason": "reason",
        "submitter": "submitter_id",
        "workflow_state": "workflow_state",
        "category": "category",
        "vote_result": "vote_result",
        "final_notes": "final_notes",
        "attachments": "attachments",
        "created": "created",
        "updated": "updated",
    },
    "polls": {
        "id": "id",
        "motion": "motion_id",
        "meeting": "meeting_id",
        "title": "title",
        "description": "description",
        "poll_type": "poll_type",
        "options": "options",
        "status": "status",
        "results": "results",
        "anonymous": "anonymous",
        "opened_at": "opened_at",
        "closed_at": "closed_at",
        "created_by": "created_by_id",
        "poll_category": "poll_category",
        "winning_option": "winning_option",
        "created": "created",
        "updated": "updated",
    },
    "votes": {
        "id": "id",
        "poll": "poll_id",
        "user": "user_id",
        "value": "value",
        "weight": "weight",
        "delegated_from": "delegated_from_id",
        "created": "created",
        "updated": "updated",
    },
}


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse a datetime string from PocketBase format."""
    if not value:
        return None
    try:
        # PocketBase uses ISO format with Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_json(value: str) -> Any:
    """Parse a JSON string from PocketBase."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def get_pocketbase_data(pb_path: str, collection: str) -> list[dict]:
    """Fetch all records from a PocketBase collection."""
    conn = sqlite3.connect(pb_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # PocketBase stores records in collection-named tables
    try:
        cursor.execute(f"SELECT * FROM {collection}")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        print(f"Warning: Could not read collection '{collection}': {e}")
        return []
    finally:
        conn.close()


def transform_record(collection: str, record: dict) -> dict:
    """Transform a PocketBase record to PostgreSQL format."""
    mapping = COLUMN_MAPPINGS.get(collection, {})
    transformed = {}

    for pb_col, pg_col in mapping.items():
        if pb_col in record:
            value = record[pb_col]

            # Transform value based on column type
            if pg_col.endswith("_id") and value == "":
                value = None
            elif pg_col in ["created", "updated", "joined_at", "invited_at", "opened_at", "closed_at", "generated_at", "approved_at", "sent_at", "scheduled_at", "recording_date", "started_at", "ended_at"]:
                value = parse_datetime(value)
            elif pg_col in ["settings", "permissions", "options", "results", "vote_result", "attachments", "default_agenda", "decisions", "attendance_snapshot", "metadata"]:
                value = parse_json(value)
            elif pg_col == "value" and collection == "votes":
                value = parse_json(value) if isinstance(value, str) else {"choice": value}
            elif isinstance(value, str) and value == "":
                value = None

            transformed[pg_col] = value

    return transformed


def migrate_collection(pb_path: str, pg_conn, collection: str, table: str) -> int:
    """Migrate a single collection from PocketBase to PostgreSQL."""
    records = get_pocketbase_data(pb_path, collection)
    if not records:
        print(f"  No records in {collection}")
        return 0

    cursor = pg_conn.cursor()

    # Transform records
    transformed = [transform_record(collection, r) for r in records]

    if not transformed:
        return 0

    # Get column names from first record
    columns = list(transformed[0].keys())

    # Build INSERT statement
    placeholders = ", ".join(["%s"] * len(columns))
    column_names = ", ".join(columns)
    insert_sql = f"""
        INSERT INTO {table} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET
        {', '.join(f'{c} = EXCLUDED.{c}' for c in columns if c != 'id')}
    """

    # Insert records
    count = 0
    for record in transformed:
        try:
            values = [record.get(c) for c in columns]
            cursor.execute(insert_sql, values)
            count += 1
        except Exception as e:
            print(f"  Error inserting record {record.get('id')}: {e}")
            continue

    pg_conn.commit()
    print(f"  Migrated {count}/{len(records)} records from {collection}")
    return count


def migrate_committee_admins(pb_path: str, pg_conn) -> int:
    """Migrate committee admins (many-to-many relationship)."""
    records = get_pocketbase_data(pb_path, "committees")
    if not records:
        return 0

    cursor = pg_conn.cursor()
    count = 0

    for record in records:
        admins = record.get("admins", "")
        if admins:
            # PocketBase stores relations as JSON array or comma-separated
            try:
                admin_ids = json.loads(admins) if admins.startswith("[") else admins.split(",")
                for admin_id in admin_ids:
                    admin_id = admin_id.strip()
                    if admin_id:
                        try:
                            cursor.execute("""
                                INSERT INTO committee_admins (committee_id, user_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (record["id"], admin_id))
                            count += 1
                        except Exception:
                            continue
            except (json.JSONDecodeError, TypeError):
                pass

    pg_conn.commit()
    print(f"  Migrated {count} committee admin relationships")
    return count


def migrate_motion_supporters(pb_path: str, pg_conn) -> int:
    """Migrate motion supporters (many-to-many relationship)."""
    records = get_pocketbase_data(pb_path, "motions")
    if not records:
        return 0

    cursor = pg_conn.cursor()
    count = 0

    for record in records:
        supporters = record.get("supporters", "")
        if supporters:
            try:
                supporter_ids = json.loads(supporters) if supporters.startswith("[") else supporters.split(",")
                for supporter_id in supporter_ids:
                    supporter_id = supporter_id.strip()
                    if supporter_id:
                        try:
                            cursor.execute("""
                                INSERT INTO motion_supporters (motion_id, user_id)
                                VALUES (%s, %s)
                                ON CONFLICT DO NOTHING
                            """, (record["id"], supporter_id))
                            count += 1
                        except Exception:
                            continue
            except (json.JSONDecodeError, TypeError):
                pass

    pg_conn.commit()
    print(f"  Migrated {count} motion supporter relationships")
    return count


def main():
    parser = argparse.ArgumentParser(description="Migrate PocketBase data to PostgreSQL")
    parser.add_argument(
        "--pb-path",
        default="./pocketbase/pb_data/data.db",
        help="Path to PocketBase SQLite database"
    )
    parser.add_argument(
        "--pg-url",
        default="postgresql://orgmeet:orgmeet@localhost:5432/orgmeet",
        help="PostgreSQL connection URL"
    )
    args = parser.parse_args()

    print(f"Migrating from: {args.pb_path}")
    print(f"Migrating to: {args.pg_url.split('@')[1] if '@' in args.pg_url else args.pg_url}")
    print()

    # Connect to PostgreSQL
    try:
        pg_conn = psycopg2.connect(args.pg_url)
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sys.exit(1)

    # Migration order (respecting foreign key constraints)
    migration_order = [
        ("users", "users"),
        ("organizations", "organizations"),
        ("org_memberships", "org_memberships"),
        ("committees", "committees"),
        ("meetings", "meetings"),
        ("participants", "participants"),
        ("agenda_items", "agenda_items"),
        ("motions", "motions"),
        ("polls", "polls"),
        ("votes", "votes"),
        ("speaker_queue", "speaker_queue"),
        ("chat_messages", "chat_messages"),
        ("meeting_templates", "meeting_templates"),
        ("meeting_minutes", "meeting_minutes"),
        ("meeting_notifications", "meeting_notifications"),
        ("files", "files"),
        ("ai_integrations", "ai_integrations"),
        ("recordings", "recordings"),
    ]

    total = 0
    for collection, table in migration_order:
        print(f"Migrating {collection}...")
        try:
            count = migrate_collection(args.pb_path, pg_conn, collection, table)
            total += count
        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Migrate many-to-many relationships
    print("\nMigrating relationships...")
    migrate_committee_admins(args.pb_path, pg_conn)
    migrate_motion_supporters(args.pb_path, pg_conn)

    pg_conn.close()
    print(f"\nMigration complete! Total records migrated: {total}")


if __name__ == "__main__":
    main()
