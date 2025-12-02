"""Tests for recordings router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recording_crud(client: AsyncClient, auth_headers: dict, test_org, test_user, db_session):
    # Need a meeting to attach recording
    meeting_resp = await client.post(
        "/api/collections/meetings/records",
        headers=auth_headers,
        json={
            "title": "Test Meeting",
            "description": "desc",
            "start_time": "2025-01-01T10:00:00Z",
            "status": "scheduled"
        }
    )
    assert meeting_resp.status_code == 200, meeting_resp.text
    meeting_id = meeting_resp.json()["id"]

    # Create recording
    rec_resp = await client.post(
        "/api/collections/recordings/records",
        headers=auth_headers,
        json={
            "meeting": meeting_id,
            "title": "Session 1",
            "provider": "local",
            "visibility": "members"
        }
    )
    assert rec_resp.status_code == 200, rec_resp.text
    rec = rec_resp.json()
    rec_id = rec["id"]
    assert rec["title"] == "Session 1"

    # List recordings
    list_resp = await client.get(f"/api/collections/recordings/records?filter=meeting=\"{meeting_id}\"", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["totalItems"] == 1

    # Update recording
    upd_resp = await client.patch(
        f"/api/collections/recordings/records/{rec_id}",
        headers=auth_headers,
        json={"title": "Session 1 Updated", "status": "archived"}
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["title"] == "Session 1 Updated"
    assert upd_resp.json()["status"] == "archived"

    # Delete
    del_resp = await client.delete(f"/api/collections/recordings/records/{rec_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Ensure gone
    list_resp2 = await client.get(f"/api/collections/recordings/records?filter=meeting=\"{meeting_id}\"", headers=auth_headers)
    assert list_resp2.status_code == 200
    assert list_resp2.json()["totalItems"] == 0
