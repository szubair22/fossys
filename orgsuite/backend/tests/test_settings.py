"""
Tests for Admin Settings API endpoints.

Covers:
- AppSetting CRUD (superadmin only)
- OrgSetting CRUD (org admin only)
- Effective settings endpoint
- Authorization checks
"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.app_setting import AppSetting
from app.models.org_setting import OrgSetting, SettingScope
from app.core.security import get_password_hash, create_access_token


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def superadmin_user(db_session: AsyncSession) -> User:
    """Create a superadmin user."""
    user = User(
        email="superadmin@example.com",
        name="Super Admin",
        password_hash=get_password_hash("SuperAdmin123"),
        verified=True,
        is_superadmin=True,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def superadmin_token(superadmin_user: User) -> str:
    """Create an access token for the superadmin user."""
    return create_access_token(data={"sub": superadmin_user.id})


@pytest.fixture
async def superadmin_headers(superadmin_token: str) -> dict:
    """Create authorization headers for superadmin."""
    return {"Authorization": f"Bearer {superadmin_token}"}


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular (non-admin) user."""
    user = User(
        email="regular@example.com",
        name="Regular User",
        password_hash=get_password_hash("Regular123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def regular_user_token(regular_user: User) -> str:
    """Create an access token for the regular user."""
    return create_access_token(data={"sub": regular_user.id})


@pytest.fixture
async def regular_headers(regular_user_token: str) -> dict:
    """Create authorization headers for regular user."""
    return {"Authorization": f"Bearer {regular_user_token}"}


@pytest.fixture
async def org_with_viewer(db_session: AsyncSession, test_org: Organization, regular_user: User) -> Organization:
    """Add regular_user as viewer to test_org."""
    membership = OrgMembership(
        organization_id=test_org.id,
        user_id=regular_user.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(membership)
    await db_session.flush()
    return test_org


# ============================================================================
# APP SETTINGS TESTS
# ============================================================================

class TestAppSettingsCRUD:
    """Test global app settings CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_app_settings_empty(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test listing app settings when empty."""
        response = await client.get(
            "/api/v1/admin/app-settings",
            headers=superadmin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_app_settings_unauthorized(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that regular users cannot list app settings."""
        response = await client.get(
            "/api/v1/admin/app-settings",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "Superadmin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_app_setting_via_upsert(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test creating an app setting via PUT (upsert)."""
        response = await client.put(
            "/api/v1/admin/app-settings/test_key",
            json={"value": {"foo": "bar"}, "description": "Test setting"},
            headers=superadmin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test_key"
        assert data["value"] == {"foo": "bar"}
        assert data["description"] == "Test setting"
        assert "id" in data
        assert "created" in data

    @pytest.mark.asyncio
    async def test_update_app_setting_via_upsert(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test updating an existing app setting via PUT (upsert)."""
        # Create first
        await client.put(
            "/api/v1/admin/app-settings/update_test",
            json={"value": "initial"},
            headers=superadmin_headers
        )

        # Update
        response = await client.put(
            "/api/v1/admin/app-settings/update_test",
            json={"value": "updated"},
            headers=superadmin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "updated"

    @pytest.mark.asyncio
    async def test_get_app_setting(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test getting a single app setting."""
        # Create first
        await client.put(
            "/api/v1/admin/app-settings/get_test",
            json={"value": {"test": True}},
            headers=superadmin_headers
        )

        # Get
        response = await client.get(
            "/api/v1/admin/app-settings/get_test",
            headers=superadmin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "get_test"
        assert data["value"] == {"test": True}

    @pytest.mark.asyncio
    async def test_get_app_setting_not_found(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test getting a non-existent app setting."""
        response = await client.get(
            "/api/v1/admin/app-settings/nonexistent",
            headers=superadmin_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_app_setting(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test deleting an app setting."""
        # Create first
        await client.put(
            "/api/v1/admin/app-settings/delete_test",
            json={"value": "to_delete"},
            headers=superadmin_headers
        )

        # Delete
        response = await client.delete(
            "/api/v1/admin/app-settings/delete_test",
            headers=superadmin_headers
        )
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(
            "/api/v1/admin/app-settings/delete_test",
            headers=superadmin_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bulk_upsert_app_settings(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        """Test bulk creating/updating app settings."""
        settings = {
            "bulk_key1": {"a": 1},
            "bulk_key2": {"b": 2},
            "bulk_key3": "string_value"
        }
        response = await client.post(
            "/api/v1/admin/app-settings/bulk",
            json=settings,
            headers=superadmin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_public_features_endpoint(
        self, client: AsyncClient
    ):
        """Test public features endpoint (no auth required)."""
        response = await client.get("/api/v1/admin/app-settings/public/features")
        assert response.status_code == 200
        data = response.json()
        # Should return defaults
        assert "enable_governance" in data
        assert "enable_membership" in data

    @pytest.mark.asyncio
    async def test_public_branding_endpoint(
        self, client: AsyncClient
    ):
        """Test public branding endpoint (no auth required)."""
        response = await client.get("/api/v1/admin/app-settings/public/branding")
        assert response.status_code == 200
        data = response.json()
        # Should return defaults
        assert data["app_name"] == "OrgSuite"


# ============================================================================
# ORG SETTINGS TESTS
# ============================================================================

class TestOrgSettingsCRUD:
    """Test organization settings CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_org_settings_empty(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test listing org settings when empty."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_org_settings_unauthorized(
        self, client: AsyncClient, regular_headers: dict, org_with_viewer: Organization
    ):
        """Test that viewers cannot access org settings."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={org_with_viewer.id}",
            headers=regular_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_org_setting(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating an org setting."""
        response = await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "governance",
                "key": "governance_config",
                "value": {"default_duration": 60}
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["organization_id"] == test_org.id
        assert data["scope"] == "governance"
        assert data["key"] == "governance_config"
        assert data["value"]["default_duration"] == 60

    @pytest.mark.asyncio
    async def test_create_org_setting_duplicate_key(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating duplicate org setting fails."""
        # Create first
        await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "governance",
                "key": "duplicate_key",
                "value": "first"
            },
            headers=auth_headers
        )

        # Try to create duplicate
        response = await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "governance",
                "key": "duplicate_key",
                "value": "second"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_org_setting(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting a single org setting."""
        # Create first
        create_response = await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "membership",
                "key": "get_test",
                "value": {"member_types": ["Regular", "Board"]}
            },
            headers=auth_headers
        )
        setting_id = create_response.json()["id"]

        # Get
        response = await client.get(
            f"/api/v1/admin/org-settings/{setting_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "get_test"
        assert data["value"]["member_types"] == ["Regular", "Board"]

    @pytest.mark.asyncio
    async def test_update_org_setting(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test updating an org setting."""
        # Create first
        create_response = await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "finance",
                "key": "update_test",
                "value": {"currency": "USD"}
            },
            headers=auth_headers
        )
        setting_id = create_response.json()["id"]

        # Update
        response = await client.patch(
            f"/api/v1/admin/org-settings/{setting_id}",
            json={"value": {"currency": "EUR"}},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["currency"] == "EUR"

    @pytest.mark.asyncio
    async def test_delete_org_setting(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test deleting an org setting."""
        # Create first
        create_response = await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "general",
                "key": "delete_test",
                "value": "to_delete"
            },
            headers=auth_headers
        )
        setting_id = create_response.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/admin/org-settings/{setting_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(
            f"/api/v1/admin/org-settings/{setting_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upsert_org_setting_by_key(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test upserting org setting by key."""
        # Create
        response = await client.put(
            f"/api/v1/admin/org-settings/by-key?organization_id={test_org.id}&scope=governance&key=upsert_test",
            json={"value": {"initial": True}},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["value"]["initial"] == True

        # Update same key
        response = await client.put(
            f"/api/v1/admin/org-settings/by-key?organization_id={test_org.id}&scope=governance&key=upsert_test",
            json={"value": {"initial": False, "updated": True}},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["initial"] == False
        assert data["value"]["updated"] == True


# ============================================================================
# EFFECTIVE SETTINGS TESTS
# ============================================================================

class TestEffectiveSettings:
    """Test effective (merged) settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_effective_settings_empty(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting effective settings when none exist."""
        response = await client.get(
            f"/api/v1/admin/org-settings/effective?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == test_org.id
        assert data["settings"] == {}

    @pytest.mark.asyncio
    async def test_get_effective_settings_with_data(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting effective settings with multiple scopes."""
        # Create settings in different scopes
        await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "governance",
                "key": "governance_config",
                "value": {"quorum": 50}
            },
            headers=auth_headers
        )
        await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "membership",
                "key": "membership_config",
                "value": {"require_email": True}
            },
            headers=auth_headers
        )

        # Get effective settings
        response = await client.get(
            f"/api/v1/admin/org-settings/effective?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "governance" in data["settings"]
        assert "membership" in data["settings"]
        assert data["settings"]["governance"]["quorum"] == 50
        assert data["settings"]["membership"]["require_email"] == True

    @pytest.mark.asyncio
    async def test_get_effective_settings_filtered_by_scope(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting effective settings filtered by scope."""
        # Create settings in different scopes
        await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "governance",
                "key": "scope_test",
                "value": {"gov": True}
            },
            headers=auth_headers
        )
        await client.post(
            "/api/v1/admin/org-settings",
            json={
                "organization_id": test_org.id,
                "scope": "finance",
                "key": "scope_test",
                "value": {"fin": True}
            },
            headers=auth_headers
        )

        # Get only governance scope
        response = await client.get(
            f"/api/v1/admin/org-settings/effective?organization_id={test_org.id}&scope=governance",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert "governance" in data["settings"]
        assert "finance" not in data["settings"]


# ============================================================================
# AUTHORIZATION TESTS
# ============================================================================

class TestSettingsAuthorization:
    """Test authorization for settings endpoints."""

    @pytest.mark.asyncio
    async def test_superadmin_can_access_any_org_settings(
        self, client: AsyncClient, superadmin_headers: dict, test_org: Organization
    ):
        """Test that superadmin can access any org's settings."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={test_org.id}",
            headers=superadmin_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_org_admin_can_access_org_settings(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test that org admin/owner can access org settings."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_org_settings(
        self, client: AsyncClient, regular_headers: dict, org_with_viewer: Organization
    ):
        """Test that viewer cannot access org settings."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={org_with_viewer.id}",
            headers=regular_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_member_cannot_access_org_settings(
        self, client: AsyncClient, regular_headers: dict, test_org: Organization
    ):
        """Test that non-member cannot access org settings."""
        response = await client.get(
            f"/api/v1/admin/org-settings?organization_id={test_org.id}",
            headers=regular_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_app_settings(
        self, client: AsyncClient, regular_headers: dict
    ):
        """Test that regular user cannot access app settings."""
        response = await client.get(
            "/api/v1/admin/app-settings",
            headers=regular_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_org_settings_require_org_to_exist(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that accessing settings for non-existent org fails."""
        response = await client.get(
            "/api/v1/admin/org-settings?organization_id=nonexistent123",
            headers=auth_headers
        )
        assert response.status_code == 404
