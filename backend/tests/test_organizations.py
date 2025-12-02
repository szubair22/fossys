"""
Tests for Organizations API endpoints.
"""
import pytest
from httpx import AsyncClient


class TestOrganizationsCRUD:
    """Test Organization CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_organizations_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing organizations when user has none."""
        response = await client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["totalItems"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_organizations_with_org(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing organizations when user has one."""
        response = await client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test Organization"
        assert data["items"][0]["user_role"] == "owner"

    @pytest.mark.asyncio
    async def test_create_organization(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new organization."""
        org_data = {
            "name": "New Test Organization",
            "description": "A new organization for testing"
        }
        response = await client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Organization"
        assert data["description"] == "A new organization for testing"
        assert data["user_role"] == "owner"
        assert "id" in data
        assert "created" in data

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_name(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating organization with duplicate name fails."""
        org_data = {"name": "Test Organization"}
        response = await client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_organization_missing_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating organization without name fails."""
        response = await client.post(
            "/api/v1/organizations",
            json={"description": "No name"},
            headers=auth_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_organization(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test getting a single organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_org.id
        assert data["name"] == "Test Organization"
        assert data["user_role"] == "owner"

    @pytest.mark.asyncio
    async def test_get_organization_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a non-existent organization."""
        response = await client.get(
            "/api/v1/organizations/nonexistent123",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_organization(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test updating an organization."""
        update_data = {
            "name": "Updated Organization Name",
            "description": "Updated description"
        }
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Organization Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_organization_partial(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test partial update of an organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            json={"description": "Only description updated"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Organization"  # Unchanged
        assert data["description"] == "Only description updated"

    @pytest.mark.asyncio
    async def test_delete_organization(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test deleting an organization."""
        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a non-existent organization."""
        response = await client.delete(
            "/api/v1/organizations/nonexistent123",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestOrganizationsSearch:
    """Test Organization search functionality."""

    @pytest.mark.asyncio
    async def test_search_organizations(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test searching organizations by name."""
        response = await client.get(
            "/api/v1/organizations?search=Test",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_search_organizations_no_match(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test searching organizations with no matches."""
        response = await client.get(
            "/api/v1/organizations?search=NonExistent",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0


class TestOrganizationsPagination:
    """Test Organization pagination."""

    @pytest.mark.asyncio
    async def test_pagination_params(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test pagination parameters."""
        response = await client.get(
            "/api/v1/organizations?page=1&perPage=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["perPage"] == 10


class TestOrganizationsAuth:
    """Test Organization authentication requirements."""

    @pytest.mark.asyncio
    async def test_list_organizations_unauthorized(self, client: AsyncClient):
        """Test listing organizations without authentication."""
        response = await client.get("/api/v1/organizations")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_organization_unauthorized(self, client: AsyncClient):
        """Test creating organization without authentication."""
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Test"}
        )
        assert response.status_code == 401
