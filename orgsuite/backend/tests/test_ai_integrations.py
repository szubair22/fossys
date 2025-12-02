"""Tests for AI integrations router."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_integration_crud(client: AsyncClient, auth_headers: dict, test_org):
    # Create
    create_resp = await client.post(
        "/api/collections/ai_integrations/records",
        headers=auth_headers,
        json={
            "organization": test_org.id,
            "provider": "openai",
            "api_key": "sk-test-123",
            "model": "gpt-4o-mini"
        }
    )
    assert create_resp.status_code == 200, create_resp.text
    ai = create_resp.json()
    ai_id = ai["id"]
    assert ai["provider"] == "openai"

    # List
    list_resp = await client.get(f"/api/collections/ai_integrations/records?filter=organization=\"{test_org.id}\"", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["totalItems"] == 1

    # Update usage
    upd_resp = await client.patch(
        f"/api/collections/ai_integrations/records/{ai_id}",
        headers=auth_headers,
        json={"usage_count": 5, "is_active": False}
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["usage_count"] == 5
    assert upd_resp.json()["is_active"] is False

    # Delete
    del_resp = await client.delete(f"/api/collections/ai_integrations/records/{ai_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Confirm removal
    list_resp2 = await client.get(f"/api/collections/ai_integrations/records?filter=organization=\"{test_org.id}\"", headers=auth_headers)
    assert list_resp2.status_code == 200
    assert list_resp2.json()["totalItems"] == 0
