"""
PostgreSQL Integration Tests for OrgSuite.

These tests verify that all APIs work correctly against a real PostgreSQL database,
catching issues that SQLite-based unit tests might miss (data types, constraints, etc.).

Run with: pytest --postgres tests/test_postgres_integration.py
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import fixtures from postgres conftest
from tests.conftest_postgres import (
    pg_engine, pg_session, pg_client, pg_test_user, pg_test_user_token,
    pg_auth_headers, pg_test_org, pg_test_member, pg_test_contact,
    pg_test_account, pg_test_committee, pg_test_meeting
)


pytestmark = pytest.mark.postgres


class TestPostgresOrganizations:
    """PostgreSQL integration tests for Organizations."""

    async def test_create_organization(self, pg_client: AsyncClient, pg_auth_headers: dict):
        """Test creating an organization with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/organizations",
            json={
                "name": "PostgreSQL Test Org",
                "description": "Created in PostgreSQL",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PostgreSQL Test Org"
        assert "id" in data

    async def test_list_organizations(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org):
        """Test listing organizations from PostgreSQL."""
        response = await pg_client.get(
            "/api/v1/organizations",
            headers=pg_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1


class TestPostgresMembers:
    """PostgreSQL integration tests for Members."""

    async def test_create_member(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org):
        """Test creating a member with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/membership/members",
            json={
                "organization_id": pg_test_org.id,
                "name": "PostgreSQL Member",
                "email": "pg_member@example.com",
                "status": "active",
                "member_type": "regular",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PostgreSQL Member"

    async def test_list_members(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org, pg_test_member):
        """Test listing members from PostgreSQL."""
        response = await pg_client.get(
            f"/api/v1/membership/members?organization_id={pg_test_org.id}",
            headers=pg_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1


class TestPostgresAccounts:
    """PostgreSQL integration tests for Accounts."""

    async def test_create_account(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org):
        """Test creating an account with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/finance/accounts",
            json={
                "organization_id": pg_test_org.id,
                "code": "2000",
                "name": "PostgreSQL Account",
                "account_type": "liability",
                "account_subtype": "accounts_payable",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PostgreSQL Account"

    async def test_list_accounts(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org, pg_test_account):
        """Test listing accounts from PostgreSQL."""
        response = await pg_client.get(
            f"/api/v1/finance/accounts?organization_id={pg_test_org.id}",
            headers=pg_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1


class TestPostgresJournalEntries:
    """PostgreSQL integration tests for Journal Entries."""

    async def test_create_journal_entry(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org, pg_test_account, pg_session):
        """Test creating a journal entry with PostgreSQL."""
        from app.models.account import Account, AccountType, AccountSubtype

        # Create a revenue account for the credit side
        revenue_account = Account(
            organization_id=pg_test_org.id,
            code="4000",
            name="PG Revenue",
            account_type=AccountType.REVENUE,
            account_subtype=AccountSubtype.DONATIONS,
            is_active=True,
            is_system=False,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        pg_session.add(revenue_account)
        await pg_session.flush()

        response = await pg_client.post(
            "/api/v1/finance/journal",
            json={
                "organization_id": pg_test_org.id,
                "entry_date": datetime.now(timezone.utc).date().isoformat(),
                "description": "PostgreSQL test entry",
                "lines": [
                    {"account_id": pg_test_account.id, "debit": 100.00, "credit": 0},
                    {"account_id": revenue_account.id, "debit": 0, "credit": 100.00},
                ],
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "PostgreSQL test entry"

    async def test_post_journal_entry(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org, pg_test_account, pg_session):
        """Test posting a journal entry with PostgreSQL."""
        from app.models.account import Account, AccountType, AccountSubtype

        # Create a revenue account
        revenue_account = Account(
            organization_id=pg_test_org.id,
            code="4001",
            name="PG Revenue 2",
            account_type=AccountType.REVENUE,
            account_subtype=AccountSubtype.DONATIONS,
            is_active=True,
            is_system=False,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        pg_session.add(revenue_account)
        await pg_session.flush()

        # Create entry
        create_response = await pg_client.post(
            "/api/v1/finance/journal",
            json={
                "organization_id": pg_test_org.id,
                "entry_date": datetime.now(timezone.utc).date().isoformat(),
                "description": "Entry to post",
                "lines": [
                    {"account_id": pg_test_account.id, "debit": 50.00, "credit": 0},
                    {"account_id": revenue_account.id, "debit": 0, "credit": 50.00},
                ],
            },
            headers=pg_auth_headers,
        )
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # Post the entry
        post_response = await pg_client.post(
            f"/api/v1/finance/journal/{entry_id}/post",
            headers=pg_auth_headers,
        )
        assert post_response.status_code == 200
        assert post_response.json()["status"] == "posted"


class TestPostgresGovernance:
    """PostgreSQL integration tests for Governance module."""

    async def test_create_committee(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org):
        """Test creating a committee with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/governance/committees",
            json={
                "organization_id": pg_test_org.id,
                "name": "PostgreSQL Committee",
                "description": "Created in PostgreSQL",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "PostgreSQL Committee"

    async def test_create_meeting(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_committee):
        """Test creating a meeting with PostgreSQL."""
        start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = await pg_client.post(
            "/api/v1/governance/meetings",
            json={
                "title": "PostgreSQL Meeting",
                "description": "A PostgreSQL test meeting",
                "start_time": start_time,
                "status": "scheduled",
                "meeting_type": "general",
                "committee_id": pg_test_committee.id,
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "PostgreSQL Meeting"
        assert data["jitsi_room"] is not None

    async def test_create_agenda_item(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_meeting):
        """Test creating an agenda item with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/governance/agenda-items",
            json={
                "meeting_id": pg_test_meeting.id,
                "title": "PostgreSQL Agenda Item",
                "description": "Discussion topic",
                "item_type": "topic",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "PostgreSQL Agenda Item"

    async def test_create_motion(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_meeting):
        """Test creating a motion with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/governance/motions",
            json={
                "meeting_id": pg_test_meeting.id,
                "title": "PostgreSQL Motion",
                "text": "Be it resolved that PostgreSQL works correctly.",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "PostgreSQL Motion"
        assert data["workflow_state"] == "draft"

    async def test_create_poll(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_meeting):
        """Test creating a poll with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/governance/polls",
            json={
                "meeting_id": pg_test_meeting.id,
                "title": "PostgreSQL Poll",
                "poll_type": "yes_no",
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "PostgreSQL Poll"
        assert data["status"] == "draft"

    async def test_meeting_workflow(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_meeting):
        """Test full meeting workflow with PostgreSQL."""
        # Update to in_progress
        update_response = await pg_client.patch(
            f"/api/v1/governance/meetings/{pg_test_meeting.id}",
            json={"status": "in_progress"},
            headers=pg_auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "in_progress"

        # Close meeting
        close_response = await pg_client.post(
            f"/api/v1/governance/meetings/{pg_test_meeting.id}/close",
            headers=pg_auth_headers,
        )
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "completed"

        # Reopen meeting
        reopen_response = await pg_client.post(
            f"/api/v1/governance/meetings/{pg_test_meeting.id}/reopen",
            headers=pg_auth_headers,
        )
        assert reopen_response.status_code == 200
        assert reopen_response.json()["status"] == "in_progress"


class TestPostgresDonations:
    """PostgreSQL integration tests for Donations."""

    async def test_create_donation(self, pg_client: AsyncClient, pg_auth_headers: dict, pg_test_org, pg_test_contact):
        """Test creating a donation with PostgreSQL."""
        response = await pg_client.post(
            "/api/v1/finance/donations",
            json={
                "organization_id": pg_test_org.id,
                "donor_type": "contact",
                "donor_contact_id": pg_test_contact.id,
                "amount": 250.00,
                "status": "pledged",
                "payment_method": "credit_card",
                "donation_date": datetime.now(timezone.utc).date().isoformat(),
            },
            headers=pg_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 250.00
