"""Tests for file upload/list/get/delete endpoints."""
import os
import pytest
from httpx import AsyncClient
from app.core.config import settings

# Use project-local upload dir to avoid permission issues
settings.UPLOAD_DIR = os.path.abspath("./test_uploads")


@pytest.mark.asyncio
async def test_file_crud(client: AsyncClient, auth_headers: dict, test_org):
    # Upload a file
    files = {"upload": ("hello.txt", b"Hello World", "text/plain")}
    data = {
        "organization": test_org.id,
        "name": "hello.txt",
        "description": "Test file",
    }
    resp = await client.post(
        "/api/collections/files/records",
        headers=auth_headers,
        files=files,
        data=data,
    )
    assert resp.status_code == 200, resp.text
    file_record = resp.json()
    file_id = file_record["id"]
    assert file_record["name"] == "hello.txt"
    assert file_record["organization"] == test_org.id

    # List files filtered by organization
    list_resp = await client.get(
        f"/api/collections/files/records?filter=organization='{test_org.id}'",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    data_json = list_resp.json()
    assert data_json["totalItems"] == 1
    assert data_json["items"][0]["id"] == file_id

    # Get single file metadata
    get_resp = await client.get(
        f"/api/collections/files/records/{file_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == file_id

    # Download file
    dl_resp = await client.get(
        f"/api/collections/files/records/{file_id}/download",
        headers=auth_headers,
    )
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"Hello World"

    # Delete file
    del_resp = await client.delete(
        f"/api/collections/files/records/{file_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204

    # Ensure list now empty
    list_resp2 = await client.get(
        f"/api/collections/files/records?filter=organization='{test_org.id}'",
        headers=auth_headers,
    )
    assert list_resp2.status_code == 200
    assert list_resp2.json()["totalItems"] == 0
