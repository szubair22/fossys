"""
Tests for Finance API endpoints (Accounts, Journal Entries, Donations).
"""
import pytest
from httpx import AsyncClient
from datetime import date
from decimal import Decimal


class TestAccountsCRUD:
    """Test Account CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_accounts_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing accounts when org has none."""
        response = await client.get(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_list_accounts_with_account(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test listing accounts when org has one."""
        response = await client.get(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert data["items"][0]["code"] == "1000"
        assert data["items"][0]["account_type"] == "asset"

    @pytest.mark.asyncio
    async def test_create_account(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating a new account."""
        account_data = {
            "code": "2000",
            "name": "Accounts Payable",
            "account_type": "liability",
            "account_subtype": "accounts_payable"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "2000"
        assert data["name"] == "Accounts Payable"
        assert data["account_type"] == "liability"

    @pytest.mark.asyncio
    async def test_create_account_duplicate_code(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test creating account with duplicate code fails."""
        account_data = {
            "code": "1000",  # Same as test_account
            "name": "Another Cash",
            "account_type": "asset"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_account(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test updating an account."""
        update_data = {"name": "Petty Cash", "is_active": False}
        response = await client.patch(
            f"/api/v1/finance/accounts/{test_account.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Petty Cash"
        assert data["is_active"] == False

    @pytest.mark.asyncio
    async def test_delete_account(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test deleting a non-system account."""
        response = await client.delete(
            f"/api/v1/finance/accounts/{test_account.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


class TestAccountTypeConsistency:
    """Test Account type and subtype consistency."""

    @pytest.mark.asyncio
    async def test_asset_subtypes(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test that asset accounts can have asset subtypes."""
        account_data = {
            "code": "1100",
            "name": "Bank Account",
            "account_type": "asset",
            "account_subtype": "bank"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        assert response.json()["account_subtype"] == "bank"

    @pytest.mark.asyncio
    async def test_liability_subtypes(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test liability account subtypes."""
        account_data = {
            "code": "2100",
            "name": "Credit Card",
            "account_type": "liability",
            "account_subtype": "credit_card"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_revenue_subtypes(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test revenue account subtypes."""
        account_data = {
            "code": "4100",
            "name": "Membership Dues",
            "account_type": "revenue",
            "account_subtype": "dues"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_expense_subtypes(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test expense account subtypes."""
        account_data = {
            "code": "5100",
            "name": "Office Supplies",
            "account_type": "expense",
            "account_subtype": "supplies"
        }
        response = await client.post(
            f"/api/v1/finance/accounts?organization_id={test_org.id}",
            json=account_data,
            headers=auth_headers
        )
        assert response.status_code == 201


class TestAccountFiltering:
    """Test Account filtering functionality."""

    @pytest.mark.asyncio
    async def test_filter_by_account_type(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test filtering accounts by type."""
        response = await client.get(
            f"/api/v1/finance/accounts?organization_id={test_org.id}&account_type=asset",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

        response = await client.get(
            f"/api/v1/finance/accounts?organization_id={test_org.id}&account_type=liability",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_active_status(
        self, client: AsyncClient, auth_headers: dict, test_org, test_account
    ):
        """Test filtering accounts by active status."""
        response = await client.get(
            f"/api/v1/finance/accounts?organization_id={test_org.id}&is_active=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1


class TestJournalEntriesCRUD:
    """Test Journal Entry CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_journal_entries_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing journal entries when org has none."""
        response = await client.get(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_create_balanced_journal_entry(
        self, client: AsyncClient, auth_headers: dict, test_org,
        test_account, test_revenue_account
    ):
        """Test creating a balanced journal entry."""
        entry_data = {
            "entry_date": str(date.today()),
            "description": "Test entry",
            "lines": [
                {
                    "account_id": test_account.id,
                    "debit_amount": 100.00,
                    "credit_amount": 0
                },
                {
                    "account_id": test_revenue_account.id,
                    "debit_amount": 0,
                    "credit_amount": 100.00
                }
            ]
        }
        response = await client.post(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            json=entry_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert len(data["lines"]) == 2

    @pytest.mark.asyncio
    async def test_create_unbalanced_journal_entry_fails(
        self, client: AsyncClient, auth_headers: dict, test_org,
        test_account, test_revenue_account
    ):
        """Test that unbalanced journal entry fails."""
        entry_data = {
            "entry_date": str(date.today()),
            "description": "Unbalanced entry",
            "lines": [
                {
                    "account_id": test_account.id,
                    "debit_amount": 100.00,
                    "credit_amount": 0
                },
                {
                    "account_id": test_revenue_account.id,
                    "debit_amount": 0,
                    "credit_amount": 50.00  # Not balanced!
                }
            ]
        }
        response = await client.post(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            json=entry_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "balance" in response.json()["detail"].lower()


class TestJournalEntryPosting:
    """Test Journal Entry posting and voiding."""

    @pytest.mark.asyncio
    async def test_post_draft_entry(
        self, client: AsyncClient, auth_headers: dict, test_org,
        test_account, test_revenue_account
    ):
        """Test posting a draft journal entry."""
        # Create entry
        entry_data = {
            "entry_date": str(date.today()),
            "description": "Entry to post",
            "lines": [
                {"account_id": test_account.id, "debit_amount": 100.00, "credit_amount": 0},
                {"account_id": test_revenue_account.id, "debit_amount": 0, "credit_amount": 100.00}
            ]
        }
        response = await client.post(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            json=entry_data,
            headers=auth_headers
        )
        entry_id = response.json()["id"]

        # Post entry
        response = await client.post(
            f"/api/v1/finance/journal-entries/{entry_id}/post?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"
        assert data["posted_at"] is not None

    @pytest.mark.asyncio
    async def test_void_posted_entry(
        self, client: AsyncClient, auth_headers: dict, test_org,
        test_account, test_revenue_account
    ):
        """Test voiding a posted journal entry."""
        # Create and post entry
        entry_data = {
            "entry_date": str(date.today()),
            "description": "Entry to void",
            "lines": [
                {"account_id": test_account.id, "debit_amount": 100.00, "credit_amount": 0},
                {"account_id": test_revenue_account.id, "debit_amount": 0, "credit_amount": 100.00}
            ]
        }
        response = await client.post(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            json=entry_data,
            headers=auth_headers
        )
        entry_id = response.json()["id"]

        # Post
        await client.post(
            f"/api/v1/finance/journal-entries/{entry_id}/post?organization_id={test_org.id}",
            headers=auth_headers
        )

        # Void
        response = await client.post(
            f"/api/v1/finance/journal-entries/{entry_id}/void?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "voided"
        assert data["voided_at"] is not None

    @pytest.mark.asyncio
    async def test_cannot_void_draft_entry(
        self, client: AsyncClient, auth_headers: dict, test_org,
        test_account, test_revenue_account
    ):
        """Test that draft entries cannot be voided directly."""
        # Create entry (stays as draft)
        entry_data = {
            "entry_date": str(date.today()),
            "description": "Draft entry",
            "lines": [
                {"account_id": test_account.id, "debit_amount": 100.00, "credit_amount": 0},
                {"account_id": test_revenue_account.id, "debit_amount": 0, "credit_amount": 100.00}
            ]
        }
        response = await client.post(
            f"/api/v1/finance/journal-entries?organization_id={test_org.id}",
            json=entry_data,
            headers=auth_headers
        )
        entry_id = response.json()["id"]

        # Try to void draft
        response = await client.post(
            f"/api/v1/finance/journal-entries/{entry_id}/void?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 400


class TestDonationsCRUD:
    """Test Donation CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_donations_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test listing donations when org has none."""
        response = await client.get(
            f"/api/v1/finance/donations?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_create_donation_contact(
        self, client: AsyncClient, auth_headers: dict, test_org, test_contact
    ):
        """Test creating a donation from a contact."""
        donation_data = {
            "donor_type": "contact",
            "donor_contact_id": test_contact.id,
            "amount": 250.00,
            "status": "received",
            "payment_method": "check",
            "donation_date": str(date.today()),
            "received_date": str(date.today())
        }
        response = await client.post(
            f"/api/v1/finance/donations?organization_id={test_org.id}",
            json=donation_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 250.00
        assert data["donor_type"] == "contact"

    @pytest.mark.asyncio
    async def test_create_donation_member(
        self, client: AsyncClient, auth_headers: dict, test_org, test_member
    ):
        """Test creating a donation from a member."""
        donation_data = {
            "donor_type": "member",
            "donor_member_id": test_member.id,
            "amount": 100.00,
            "status": "received",
            "payment_method": "cash",
            "donation_date": str(date.today())
        }
        response = await client.post(
            f"/api/v1/finance/donations?organization_id={test_org.id}",
            json=donation_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["donor_type"] == "member"

    @pytest.mark.asyncio
    async def test_create_anonymous_donation(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test creating an anonymous donation."""
        donation_data = {
            "donor_type": "anonymous",
            "amount": 500.00,
            "status": "received",
            "payment_method": "cash",
            "donation_date": str(date.today())
        }
        response = await client.post(
            f"/api/v1/finance/donations?organization_id={test_org.id}",
            json=donation_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["donor_type"] == "anonymous"


class TestDonationSummary:
    """Test Donation summary endpoint."""

    @pytest.mark.asyncio
    async def test_donation_summary_empty(
        self, client: AsyncClient, auth_headers: dict, test_org
    ):
        """Test donation summary with no donations."""
        response = await client.get(
            f"/api/v1/finance/donations/summary?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_received"] == 0
        assert data["total_pending"] == 0
        assert data["total_pledged"] == 0

    @pytest.mark.asyncio
    async def test_donation_summary_with_donations(
        self, client: AsyncClient, auth_headers: dict, test_org, test_donation
    ):
        """Test donation summary with existing donation."""
        response = await client.get(
            f"/api/v1/finance/donations/summary?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_received"] == 100.00

    @pytest.mark.asyncio
    async def test_donation_summary_date_range(
        self, client: AsyncClient, auth_headers: dict, test_org, test_donation
    ):
        """Test donation summary with date range filter."""
        today = str(date.today())
        response = await client.get(
            f"/api/v1/finance/donations/summary?organization_id={test_org.id}&start_date={today}&end_date={today}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_received"] == 100.00


class TestDonationFiltering:
    """Test Donation filtering functionality."""

    @pytest.mark.asyncio
    async def test_filter_donations_by_status(
        self, client: AsyncClient, auth_headers: dict, test_org, test_donation
    ):
        """Test filtering donations by status."""
        response = await client.get(
            f"/api/v1/finance/donations?organization_id={test_org.id}&status=received",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1

        response = await client.get(
            f"/api/v1/finance/donations?organization_id={test_org.id}&status=pending",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_filter_donations_by_date_range(
        self, client: AsyncClient, auth_headers: dict, test_org, test_donation
    ):
        """Test filtering donations by date range."""
        today = str(date.today())
        response = await client.get(
            f"/api/v1/finance/donations?organization_id={test_org.id}&start_date={today}&end_date={today}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
