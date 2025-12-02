"""Tests for meeting notifications router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_meeting_notification_crud(client: AsyncClient, auth_headers: dict, test_org, test_user):
    # Create meeting first
    meeting_resp = await client.post(
        "/api/collections/meetings/records",
        headers=auth_headers,
        json={
            "title": "Notify Meeting",
            "description": "desc",
            "start_time": "2025-01-01T10:00:00Z",
            "status": "scheduled"
        }
    )
    assert meeting_resp.status_code == 200, meeting_resp.text
    meeting_id = meeting_resp.json()["id"]

    # Create notification
    create_resp = await client.post(
        "/api/collections/meeting_notifications/records",
        headers=auth_headers,
        json={
            "meeting": meeting_id,
            "recipient_user": test_user.id,
            "notification_type": "invitation"
        }
    )
    assert create_resp.status_code == 200, create_resp.text
    notif = create_resp.json()
    notif_id = notif["id"]
    assert notif["notification_type"] == "invitation"

    # List
    list_resp = await client.get(f"/api/collections/meeting_notifications/records?filter=meeting=\"{meeting_id}\"", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["totalItems"] == 1

    # Update
    upd_resp = await client.patch(
        f"/api/collections/meeting_notifications/records/{notif_id}",
        headers=auth_headers,
        json={"status": "sent", "error_message": None}
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["status"] == "sent"

    # Delete
    del_resp = await client.delete(f"/api/collections/meeting_notifications/records/{notif_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Confirm removal
    list_resp2 = await client.get(f"/api/collections/meeting_notifications/records?filter=meeting=\"{meeting_id}\"", headers=auth_headers)
    assert list_resp2.status_code == 200
    assert list_resp2.json()["totalItems"] == 0
