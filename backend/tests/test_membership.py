"""
Tests for Membership API endpoints (Members and Contacts).
"""
import pytest
from httpx import AsyncClient
from datetime import date


class TestMembersCRUD:
    """Test Member CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_members_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing members when org has none."""
        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_list_members_with_member(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test listing members when org has one."""
        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert data["items"][0]["name"] == "John Doe"
        assert data["items"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_member(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating a new member."""
        member_data = {
            "name": "New Member",
            "email": "newmember@example.com",
            "status": "active",
            "member_type": "regular",
            "join_date": str(date.today())
        }
        response = await client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json=member_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Member"
        assert data["email"] == "newmember@example.com"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_member_minimal(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating a member with minimal data."""
        member_data = {"name": "Minimal Member"}
        response = await client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json=member_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Member"
        assert data["status"] == "pending"  # Default status

    @pytest.mark.asyncio
    async def test_get_member(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test getting a single member."""
        response = await client.get(
            f"/api/v1/membership/members/{test_member.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_member.id
        assert data["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_update_member(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test updating a member."""
        update_data = {
            "name": "John Updated",
            "status": "inactive"
        }
        response = await client.patch(
            f"/api/v1/membership/members/{test_member.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Updated"
        assert data["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_delete_member(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test deleting a member."""
        response = await client.delete(
            f"/api/v1/membership/members/{test_member.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


class TestMembersFiltering:
    """Test Member filtering functionality."""

    @pytest.mark.asyncio
    async def test_filter_members_by_status(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test filtering members by status."""
        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}&status=active",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}&status=inactive",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_filter_members_by_type(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test filtering members by type."""
        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}&member_type=regular",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_search_members(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test searching members."""
        response = await client.get(
            f"/api/v1/membership/members?organization_id={test_org.id}&search=John",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1


class TestContactsCRUD:
    """Test Contact CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_contacts_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing contacts when org has none."""
        response = await client.get(
            f"/api/v1/membership/contacts?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_list_contacts_with_contact(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test listing contacts when org has one."""
        response = await client.get(
            f"/api/v1/membership/contacts?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert data["items"][0]["first_name"] == "Jane"
        assert data["items"][0]["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_create_contact(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating a new contact."""
        contact_data = {
            "first_name": "New",
            "last_name": "Contact",
            "email": "newcontact@example.com",
            "contact_type": "vendor"
        }
        response = await client.post(
            f"/api/v1/membership/contacts?organization_id={test_org.id}",
            json=contact_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "New"
        assert data["last_name"] == "Contact"
        assert data["contact_type"] == "vendor"

    @pytest.mark.asyncio
    async def test_create_contact_company(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating a contact with company name."""
        contact_data = {
            "company_name": "Test Company Inc.",
            "email": "company@example.com",
            "contact_type": "sponsor"
        }
        response = await client.post(
            f"/api/v1/membership/contacts?organization_id={test_org.id}",
            json=contact_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_name"] == "Test Company Inc."

    @pytest.mark.asyncio
    async def test_get_contact(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test getting a single contact."""
        response = await client.get(
            f"/api/v1/membership/contacts/{test_contact.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_contact.id

    @pytest.mark.asyncio
    async def test_update_contact(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test updating a contact."""
        update_data = {
            "first_name": "Jane Updated",
            "is_active": False
        }
        response = await client.patch(
            f"/api/v1/membership/contacts/{test_contact.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane Updated"
        assert data["is_active"] == False

    @pytest.mark.asyncio
    async def test_delete_contact(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test deleting a contact."""
        response = await client.delete(
            f"/api/v1/membership/contacts/{test_contact.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


class TestContactsFiltering:
    """Test Contact filtering functionality."""

    @pytest.mark.asyncio
    async def test_filter_contacts_by_type(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test filtering contacts by type."""
        response = await client.get(
            f"/api/v1/membership/contacts?organization_id={test_org.id}&contact_type=donor",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_filter_contacts_by_active_status(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test filtering contacts by active status."""
        response = await client.get(
            f"/api/v1/membership/contacts?organization_id={test_org.id}&is_active=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_search_contacts(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test searching contacts."""
        response = await client.get(
            f"/api/v1/membership/contacts?organization_id={test_org.id}&search=Jane",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1


class TestMemberStatusTransitions:
    """Test Member status transitions."""

    @pytest.mark.asyncio
    async def test_transition_pending_to_active(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test transitioning member from pending to active."""
        # Create pending member
        member_data = {"name": "Pending Member", "status": "pending"}
        response = await client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json=member_data,
            headers=auth_headers
        )
        member_id = response.json()["id"]

        # Update to active
        response = await client.patch(
            f"/api/v1/membership/members/{member_id}?organization_id={test_org.id}",
            json={"status": "active"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_transition_active_to_alumni(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test transitioning member from active to alumni."""
        response = await client.patch(
            f"/api/v1/membership/members/{test_member.id}?organization_id={test_org.id}",
            json={"status": "alumni"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "alumni"
