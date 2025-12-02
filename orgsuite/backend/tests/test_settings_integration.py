"""
Tests for settings-backed module behavior.

Tests that modules (membership, finance, governance) properly use
organization settings for validation and defaults.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_setting import OrgSetting, SettingScope
from app.models.member import Member, MemberStatus, MemberType
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.user import User
from app.services.settings import (
    get_membership_config,
    get_finance_config,
    get_governance_config,
    validate_member_type,
    validate_member_status,
    validate_payment_method,
)


class TestMembershipSettingsIntegration:
    """Test membership module uses org settings."""

    @pytest.mark.asyncio
    async def test_require_phone_validation(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test that require_phone setting is enforced on member creation."""
        # Create setting to require phone
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.MEMBERSHIP,
            key="membership_config",
            value={
                "member_types": ["Regular", "Associate"],
                "member_statuses": ["Active", "Inactive", "Pending"],
                "require_phone": True,
                "require_email": False,
            }
        )
        test_db.add(setting)
        await test_db.flush()

        # Try to create member without phone
        response = await async_client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json={
                "name": "Test Member",
                "email": "test@example.com",
                "status": "active",
                "member_type": "regular"
            },
            headers=auth_headers
        )

        # Should fail because phone is required
        assert response.status_code == 400
        assert "phone" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_member_type_validation(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test that member type is validated against settings."""
        # Create setting with limited member types
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.MEMBERSHIP,
            key="membership_config",
            value={
                "member_types": ["Regular", "Student"],
                "member_statuses": ["Active", "Inactive"],
                "require_phone": False,
                "require_email": False,
            }
        )
        test_db.add(setting)
        await test_db.flush()

        # Try to create member with invalid type
        response = await async_client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json={
                "name": "Test Member",
                "email": "test@example.com",
                "status": "active",
                "member_type": "lifetime"  # Not in allowed types
            },
            headers=auth_headers
        )

        # Should fail because "lifetime" is not in allowed types
        assert response.status_code == 400
        assert "member type" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_member_status_validation(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test that member status is validated against settings."""
        # Create setting with limited statuses
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.MEMBERSHIP,
            key="membership_config",
            value={
                "member_types": ["Regular"],
                "member_statuses": ["Active", "Inactive"],
                "require_phone": False,
                "require_email": False,
            }
        )
        test_db.add(setting)
        await test_db.flush()

        # Try to create member with invalid status
        response = await async_client.post(
            f"/api/v1/membership/members?organization_id={test_org.id}",
            json={
                "name": "Test Member",
                "email": "test@example.com",
                "status": "honorary",  # Not in allowed statuses
                "member_type": "regular"
            },
            headers=auth_headers
        )

        # Should fail because "honorary" is not in allowed statuses
        assert response.status_code == 400
        assert "status" in response.json()["detail"].lower()


class TestFinanceSettingsIntegration:
    """Test finance module uses org settings."""

    @pytest.mark.asyncio
    async def test_default_currency_from_settings(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test that donations use default currency from settings."""
        # Create finance setting with EUR currency
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.FINANCE,
            key="finance_config",
            value={
                "default_currency": "EUR",
                "payment_methods": ["Cash", "Bank Transfer"],
                "fiscal_year_start_month": 1,
                "enabled_dimensions": [],
            }
        )
        test_db.add(setting)
        await test_db.flush()

        # Get donation summary - should use EUR
        response = await async_client.get(
            f"/api/v1/finance/donations/summary?organization_id={test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["currency"] == "EUR"

    @pytest.mark.asyncio
    async def test_payment_method_validation(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test that payment methods are validated against settings."""
        # Create finance setting with limited payment methods
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.FINANCE,
            key="finance_config",
            value={
                "default_currency": "USD",
                "payment_methods": ["Cash", "Check"],
                "fiscal_year_start_month": 1,
                "enabled_dimensions": [],
            }
        )
        test_db.add(setting)
        await test_db.flush()

        # Try to create donation with invalid payment method
        response = await async_client.post(
            f"/api/v1/finance/donations?organization_id={test_org.id}",
            json={
                "donor_name": "Test Donor",
                "amount": 100.00,
                "donation_date": "2024-01-15",
                "status": "received",
                "payment_method": "cryptocurrency"  # Not in allowed methods
            },
            headers=auth_headers
        )

        # Should fail because "cryptocurrency" is not in allowed methods
        assert response.status_code == 400
        assert "payment method" in response.json()["detail"]["payment_method"]["message"].lower()


class TestSettingsService:
    """Test settings service helper functions."""

    @pytest.mark.asyncio
    async def test_get_membership_config_defaults(
        self,
        test_db: AsyncSession,
        test_org: Organization
    ):
        """Test that default membership config is returned when no settings exist."""
        config = await get_membership_config(test_db, test_org.id)

        # Should return default values
        assert "Regular" in config.member_types
        assert "Active" in config.member_statuses
        assert config.require_phone == False
        assert config.require_email == False

    @pytest.mark.asyncio
    async def test_get_membership_config_with_settings(
        self,
        test_db: AsyncSession,
        test_org: Organization
    ):
        """Test that custom membership config is returned when settings exist."""
        # Create custom setting
        setting = OrgSetting(
            organization_id=test_org.id,
            scope=SettingScope.MEMBERSHIP,
            key="membership_config",
            value={
                "member_types": ["Full", "Associate", "Honorary"],
                "member_statuses": ["Active", "Emeritus"],
                "require_phone": True,
                "require_email": True,
            }
        )
        test_db.add(setting)
        await test_db.flush()

        config = await get_membership_config(test_db, test_org.id)

        # Should return custom values
        assert config.member_types == ["Full", "Associate", "Honorary"]
        assert config.member_statuses == ["Active", "Emeritus"]
        assert config.require_phone == True
        assert config.require_email == True

    @pytest.mark.asyncio
    async def test_get_finance_config_defaults(
        self,
        test_db: AsyncSession,
        test_org: Organization
    ):
        """Test that default finance config is returned when no settings exist."""
        config = await get_finance_config(test_db, test_org.id)

        # Should return default values
        assert config.default_currency == "USD"
        assert config.fiscal_year_start_month == 1
        assert "Cash" in config.payment_methods

    @pytest.mark.asyncio
    async def test_get_governance_config_defaults(
        self,
        test_db: AsyncSession,
        test_org: Organization
    ):
        """Test that default governance config is returned when no settings exist."""
        config = await get_governance_config(test_db, test_org.id)

        # Should return default values
        assert config.default_meeting_duration_minutes == 60
        assert config.default_quorum_type == "percent"
        assert "Main Motion" in config.motion_types

    def test_validate_member_type(self):
        """Test member type validation helper."""
        from app.schemas.settings import MembershipConfig

        config = MembershipConfig(member_types=["Regular", "Student", "Staff"])

        assert validate_member_type("regular", config) == True
        assert validate_member_type("Regular", config) == True
        assert validate_member_type("STUDENT", config) == True
        assert validate_member_type("lifetime", config) == False

    def test_validate_member_status(self):
        """Test member status validation helper."""
        from app.schemas.settings import MembershipConfig

        config = MembershipConfig(member_statuses=["Active", "Inactive", "Pending"])

        assert validate_member_status("active", config) == True
        assert validate_member_status("INACTIVE", config) == True
        assert validate_member_status("suspended", config) == False

    def test_validate_payment_method(self):
        """Test payment method validation helper."""
        from app.schemas.settings import FinanceConfig

        config = FinanceConfig(payment_methods=["Cash", "Check", "Bank Transfer"])

        assert validate_payment_method("cash", config) == True
        assert validate_payment_method("bank_transfer", config) == True
        assert validate_payment_method("cryptocurrency", config) == False


class TestPublicSettingsAPI:
    """Test the public settings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_membership_settings(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test getting membership settings via API."""
        response = await async_client.get(
            f"/api/v1/settings/membership?organization_id={test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "member_types" in data
        assert "member_statuses" in data
        assert "require_phone" in data
        assert "require_email" in data

    @pytest.mark.asyncio
    async def test_get_finance_settings(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test getting finance settings via API."""
        response = await async_client.get(
            f"/api/v1/settings/finance?organization_id={test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "default_currency" in data
        assert "payment_methods" in data
        assert "fiscal_year_start_month" in data

    @pytest.mark.asyncio
    async def test_get_governance_settings(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test getting governance settings via API."""
        response = await async_client.get(
            f"/api/v1/settings/governance?organization_id={test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "default_meeting_duration_minutes" in data
        assert "motion_types" in data
        assert "vote_methods" in data

    @pytest.mark.asyncio
    async def test_get_all_settings(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        test_org: Organization,
        auth_headers: dict
    ):
        """Test getting all settings at once via API."""
        response = await async_client.get(
            f"/api/v1/settings?organization_id={test_org.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "organization_id" in data
        assert "membership" in data
        assert "governance" in data
        assert "finance" in data
        assert "general" in data

    @pytest.mark.asyncio
    async def test_settings_require_org_membership(
        self,
        async_client: AsyncClient,
        test_db: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """Test that settings API requires org membership."""
        # Create a new org without adding user as member
        other_org = Organization(name="Other Org", owner_id=test_user.id)
        test_db.add(other_org)
        await test_db.flush()

        # Note: We need to remove user's membership from this org
        # Since we just created it with owner_id, there might be no OrgMembership

        # Try to get settings for org where user is not a member
        response = await async_client.get(
            f"/api/v1/settings/membership?organization_id={other_org.id}",
            headers=auth_headers
        )

        # Should be forbidden
        assert response.status_code == 403
