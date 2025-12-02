"""
Tests for Dashboard and Org Invites functionality.
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.org_invite import OrgInvite, OrgInviteStatus, OrgInviteRole
from app.models.meeting import Meeting, MeetingStatus
from app.models.member import Member, MemberStatus, MemberType
from app.models.project import Project, ProjectStatus
from app.core.security import get_password_hash, create_access_token


# ============================================================================
# Dashboard Tests
# ============================================================================

class TestDashboardSummary:
    """Tests for dashboard summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting dashboard summary for an organization."""
        response = await client.get(
            f"/api/v1/dashboard/summary?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["organization_id"] == test_org.id
        assert data["organization_name"] == test_org.name
        assert "upcoming_meetings" in data
        assert "membership" in data
        assert "finance" in data
        assert "projects" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_unauthorized(
        self, client: AsyncClient, test_org: Organization
    ):
        """Test that dashboard requires authentication."""
        response = await client.get(
            f"/api/v1/dashboard/summary?organization_id={test_org.id}"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_non_member(
        self, client: AsyncClient, db_session: AsyncSession, test_org: Organization
    ):
        """Test that non-members cannot access dashboard."""
        # Create a different user
        other_user = User(
            email="other@example.com",
            name="Other User",
            password_hash=get_password_hash("OtherPass123"),
            verified=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        other_token = create_access_token(subject=other_user.id)
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = await client.get(
            f"/api/v1/dashboard/summary?organization_id={test_org.id}",
            headers=other_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_data(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, test_org: Organization, test_user: User
    ):
        """Test dashboard summary with actual data."""
        # Create some members
        for i in range(3):
            member = Member(
                organization_id=test_org.id,
                name=f"Member {i}",
                email=f"member{i}@example.com",
                status=MemberStatus.ACTIVE,
                member_type=MemberType.REGULAR,
            )
            db_session.add(member)

        # Create a scheduled meeting
        meeting = Meeting(
            organization_id=test_org.id,
            title="Test Meeting",
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            status=MeetingStatus.SCHEDULED,
            created_by_id=test_user.id,
        )
        db_session.add(meeting)

        # Create an active project
        project = Project(
            organization_id=test_org.id,
            name="Test Project",
            status=ProjectStatus.ACTIVE,
        )
        db_session.add(project)

        await db_session.flush()

        response = await client.get(
            f"/api/v1/dashboard/summary?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["membership"]["total_active"] == 3
        assert data["total_scheduled_meetings"] == 1
        assert data["projects"]["total_active"] == 1


# ============================================================================
# Org Invites Tests
# ============================================================================

class TestOrgInvitesCreate:
    """Tests for creating org invitations."""

    @pytest.mark.asyncio
    async def test_create_invite_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating an invitation successfully."""
        response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "newuser@example.com",
                "role": "member"
            }
        )
        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "newuser@example.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"
        assert "token" in data

    @pytest.mark.asyncio
    async def test_create_invite_with_message(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating an invitation with a personal message."""
        response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "friend@example.com",
                "role": "admin",
                "message": "Looking forward to working with you!"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_create_invite_duplicate_pending(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test that duplicate pending invites are rejected."""
        # First invite
        await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "duplicate@example.com",
                "role": "member"
            }
        )

        # Second invite to same email
        response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "duplicate@example.com",
                "role": "admin"
            }
        )
        assert response.status_code == 400
        assert "already pending" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_invite_viewer_cannot(
        self, client: AsyncClient, db_session: AsyncSession, test_org: Organization
    ):
        """Test that viewers cannot create invites."""
        # Create a viewer user
        viewer = User(
            email="viewer@example.com",
            name="Viewer User",
            password_hash=get_password_hash("ViewerPass123"),
            verified=True,
        )
        db_session.add(viewer)
        await db_session.flush()

        # Create viewer membership
        membership = OrgMembership(
            organization_id=test_org.id,
            user_id=viewer.id,
            role=OrgMembershipRole.VIEWER,
            is_active=True,
        )
        db_session.add(membership)
        await db_session.flush()

        viewer_token = create_access_token(subject=viewer.id)
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        response = await client.post(
            "/api/v1/governance/org-invites",
            headers=viewer_headers,
            json={
                "organization_id": test_org.id,
                "email": "someone@example.com",
                "role": "member"
            }
        )
        assert response.status_code == 403


class TestOrgInvitesList:
    """Tests for listing org invitations."""

    @pytest.mark.asyncio
    async def test_list_invites_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test listing invitations for an organization."""
        # Create some invites
        await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={"organization_id": test_org.id, "email": "user1@example.com", "role": "member"}
        )
        await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={"organization_id": test_org.id, "email": "user2@example.com", "role": "admin"}
        )

        response = await client.get(
            f"/api/v1/governance/org-invites/org/{test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["totalItems"] == 2
        assert len(data["items"]) == 2


class TestOrgInvitesAccept:
    """Tests for accepting org invitations."""

    @pytest.mark.asyncio
    async def test_accept_invite_success(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, test_org: Organization
    ):
        """Test accepting an invitation successfully."""
        # Create an invite
        create_response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "newmember@example.com",
                "role": "member"
            }
        )
        invite_token = create_response.json()["token"]

        # Create a new user
        new_user = User(
            email="newmember@example.com",
            name="New Member",
            password_hash=get_password_hash("NewPass123"),
            verified=True,
        )
        db_session.add(new_user)
        await db_session.flush()

        new_user_token = create_access_token(subject=new_user.id)
        new_user_headers = {"Authorization": f"Bearer {new_user_token}"}

        # Accept the invite
        response = await client.post(
            "/api/v1/governance/org-invites/accept",
            headers=new_user_headers,
            json={"token": invite_token}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["organization_id"] == test_org.id
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_accept_invite_invalid_token(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test accepting with invalid token fails."""
        response = await client.post(
            "/api/v1/governance/org-invites/accept",
            headers=auth_headers,
            json={"token": "invalid-token-12345"}
        )
        assert response.status_code == 404


class TestOrgInvitesCancel:
    """Tests for cancelling org invitations."""

    @pytest.mark.asyncio
    async def test_cancel_invite_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test cancelling an invitation successfully."""
        # Create an invite
        create_response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "tocancel@example.com",
                "role": "member"
            }
        )
        invite_id = create_response.json()["id"]

        # Cancel the invite
        response = await client.post(
            f"/api/v1/governance/org-invites/{invite_id}/cancel",
            headers=auth_headers
        )
        assert response.status_code == 204


class TestOrgInvitesResend:
    """Tests for resending org invitations."""

    @pytest.mark.asyncio
    async def test_resend_invite_success(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test resending an invitation."""
        # Create an invite
        create_response = await client.post(
            "/api/v1/governance/org-invites",
            headers=auth_headers,
            json={
                "organization_id": test_org.id,
                "email": "toresend@example.com",
                "role": "member"
            }
        )
        invite_id = create_response.json()["id"]
        original_token = create_response.json()["token"]

        # Resend the invite
        response = await client.post(
            f"/api/v1/governance/org-invites/{invite_id}/resend",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Token should be regenerated
        assert data["token"] != original_token
        assert data["status"] == "pending"
