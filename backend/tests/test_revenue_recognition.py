"""
Tests for Revenue Recognition (ASC 606) API endpoints.

Covers:
- Contract CRUD operations
- Transaction price allocation
- Revenue schedule generation (straight-line and point-in-time)
- Revenue recognition posting
- Edition guard tests (403 for disabled features)
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.org_setting import OrgSetting, SettingScope
from app.models.account import Account, AccountType, AccountSubType
from app.models.contact import Contact, ContactType
from app.core.security import create_access_token


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def revenue_account(db_session: AsyncSession, test_org: Organization) -> Account:
    """Create a revenue account for testing."""
    account = Account(
        organization_id=test_org.id,
        code="4100",
        name="Service Revenue",
        account_type=AccountType.REVENUE,
        account_subtype=AccountSubType.OTHER_INCOME,
        is_active=True,
        is_system=False,
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest.fixture
async def deferred_revenue_account(db_session: AsyncSession, test_org: Organization) -> Account:
    """Create a deferred revenue (liability) account for testing."""
    account = Account(
        organization_id=test_org.id,
        code="2400",
        name="Deferred Revenue",
        account_type=AccountType.LIABILITY,
        account_subtype=AccountSubType.OTHER_LIABILITY,
        is_active=True,
        is_system=False,
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest.fixture
async def customer_contact(db_session: AsyncSession, test_org: Organization) -> Contact:
    """Create a customer contact for contracts."""
    contact = Contact(
        organization_id=test_org.id,
        first_name="Acme",
        last_name="Corp",
        email="billing@acme.com",
        contact_type=ContactType.CUSTOMER,
        is_active=True,
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


@pytest.fixture
async def nonprofit_org(db_session: AsyncSession, test_org: Organization) -> Organization:
    """Enable contracts and rev rec features for the test org (nonprofit edition)."""
    # Set finance settings to nonprofit edition
    finance_setting = OrgSetting(
        organization_id=test_org.id,
        scope=SettingScope.FINANCE,
        key="finance_config",
        value={
            "edition": "nonprofit",
            "accounting_basis": "nonprofit_gaap",
            "enable_rev_rec": True,
            "enable_contracts": True,
            "enable_restrictions": True,
            "enable_donations": True,
        }
    )
    db_session.add(finance_setting)
    await db_session.flush()
    return test_org


@pytest.fixture
async def startup_org(db_session: AsyncSession, test_org: Organization) -> Organization:
    """Configure test org as startup edition (rev rec disabled)."""
    # Set finance settings to startup edition
    finance_setting = OrgSetting(
        organization_id=test_org.id,
        scope=SettingScope.FINANCE,
        key="finance_config",
        value={
            "edition": "startup",
            "accounting_basis": "cash",
            "enable_rev_rec": False,
            "enable_contracts": False,
            "enable_restrictions": False,
            "enable_donations": False,
        }
    )
    db_session.add(finance_setting)
    await db_session.flush()
    return test_org


# ============================================================================
# CONTRACT CRUD TESTS
# ============================================================================

class TestContractCRUD:
    """Test Contract CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_contracts_empty(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization
    ):
        """Test listing contracts when org has none."""
        response = await client.get(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_create_contract(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test creating a contract with lines."""
        today = date.today()
        end_date = today + timedelta(days=365)

        contract_data = {
            "name": "Annual Service Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "end_date": str(end_date),
            "total_transaction_price": 12000.00,
            "currency": "USD",
            "lines": [
                {
                    "description": "Monthly Subscription Service",
                    "product_type": "subscription",
                    "recognition_pattern": "straight_line",
                    "start_date": str(today),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 12000.00,
                    "ssp_amount": 12000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Annual Service Contract"
        assert data["status"] == "draft"
        assert len(data["lines"]) == 1
        assert data["lines"][0]["description"] == "Monthly Subscription Service"

    @pytest.mark.asyncio
    async def test_create_contract_multiple_lines(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test creating a contract with multiple lines for allocation testing."""
        today = date.today()
        end_date = today + timedelta(days=365)

        contract_data = {
            "name": "Bundled Service Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "end_date": str(end_date),
            "total_transaction_price": 15000.00,
            "currency": "USD",
            "lines": [
                {
                    "description": "Software License",
                    "product_type": "license",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "ssp_amount": 6000.00,  # SSP is higher than contract price
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                },
                {
                    "description": "Support Services",
                    "product_type": "service",
                    "recognition_pattern": "straight_line",
                    "start_date": str(today),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 10000.00,
                    "ssp_amount": 9000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["lines"]) == 2

    @pytest.mark.asyncio
    async def test_get_contract(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test getting a single contract."""
        today = date.today()

        # Create first
        contract_data = {
            "name": "Test Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Get
        response = await client.get(
            f"/api/v1/finance/contracts/{contract_id}?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contract_id
        assert data["name"] == "Test Contract"

    @pytest.mark.asyncio
    async def test_update_contract(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test updating a contract."""
        today = date.today()

        # Create first
        contract_data = {
            "name": "Original Name",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Update
        response = await client.patch(
            f"/api/v1/finance/contracts/{contract_id}?organization_id={nonprofit_org.id}",
            json={"name": "Updated Name", "notes": "Some notes"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["notes"] == "Some notes"

    @pytest.mark.asyncio
    async def test_delete_draft_contract(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test deleting a draft contract."""
        today = date.today()

        # Create first
        contract_data = {
            "name": "To Delete",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/finance/contracts/{contract_id}?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


# ============================================================================
# CONTRACT ACTIVATION AND ALLOCATION TESTS
# ============================================================================

class TestContractActivation:
    """Test contract activation and transaction price allocation."""

    @pytest.mark.asyncio
    async def test_activate_contract_single_line(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test activating a contract with a single line."""
        today = date.today()
        end_date = today + timedelta(days=365)

        # Create contract
        contract_data = {
            "name": "Single Line Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "end_date": str(end_date),
            "total_transaction_price": 12000.00,
            "lines": [
                {
                    "description": "Annual Service",
                    "recognition_pattern": "straight_line",
                    "start_date": str(today),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 12000.00,
                    "ssp_amount": 12000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate
        response = await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        # Single line should get full amount
        assert float(data["lines"][0]["allocated_transaction_price"]) == 12000.00

    @pytest.mark.asyncio
    async def test_activate_contract_multiple_lines_ssp_allocation(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test allocation across multiple lines using relative SSP method."""
        today = date.today()
        end_date = today + timedelta(days=365)

        # Contract with bundle discount: total $15,000 but SSP totals $16,000
        # Line 1: SSP $6,000 (37.5% of total SSP) -> should get $5,625
        # Line 2: SSP $10,000 (62.5% of total SSP) -> should get $9,375
        contract_data = {
            "name": "Bundle Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "end_date": str(end_date),
            "total_transaction_price": 15000.00,
            "lines": [
                {
                    "description": "Software License",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "ssp_amount": 6000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                },
                {
                    "description": "Support Services",
                    "recognition_pattern": "straight_line",
                    "start_date": str(today),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 10000.00,
                    "ssp_amount": 10000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate
        response = await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Check allocation sums to total
        total_allocated = sum(
            Decimal(str(line["allocated_transaction_price"]))
            for line in data["lines"]
        )
        assert total_allocated == Decimal("15000.00")

        # Check relative allocation (line 1: 6000/16000 * 15000 = 5625)
        line1 = next(l for l in data["lines"] if l["description"] == "Software License")
        line2 = next(l for l in data["lines"] if l["description"] == "Support Services")

        # Verify allocation is proportional to SSP
        assert float(line1["allocated_transaction_price"]) == 5625.00
        assert float(line2["allocated_transaction_price"]) == 9375.00


# ============================================================================
# REVENUE SCHEDULE GENERATION TESTS
# ============================================================================

class TestScheduleGeneration:
    """Test revenue schedule generation."""

    @pytest.mark.asyncio
    async def test_generate_straight_line_schedule(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test generating a straight-line schedule over 12 months."""
        # Use Jan 1 to Dec 31 for predictable monthly periods
        start_date = date(2025, 1, 1)
        end_date = date(2025, 12, 31)

        # Create and activate contract
        contract_data = {
            "name": "12-Month Service",
            "customer_contact_id": customer_contact.id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_transaction_price": 12000.00,
            "lines": [
                {
                    "description": "Monthly Service",
                    "recognition_pattern": "straight_line",
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 12000.00,
                    "ssp_amount": 12000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate to allocate price
        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )

        # Generate schedules
        response = await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["schedules_created"] == 1

        # Get schedule to verify lines
        schedules_response = await client.get(
            f"/api/v1/finance/rev-rec/schedules?organization_id={nonprofit_org.id}&contract_id={contract_id}",
            headers=auth_headers
        )
        assert schedules_response.status_code == 200
        schedules = schedules_response.json()["items"]
        assert len(schedules) == 1

        schedule = schedules[0]
        assert schedule["recognition_method"] == "straight_line"
        assert len(schedule["lines"]) == 12  # 12 months

        # Verify each line is ~$1000
        for line in schedule["lines"]:
            assert float(line["amount"]) == 1000.00

        # Verify total
        total = sum(Decimal(str(line["amount"])) for line in schedule["lines"])
        assert total == Decimal("12000.00")

    @pytest.mark.asyncio
    async def test_generate_point_in_time_schedule(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test generating a point-in-time schedule (single recognition)."""
        today = date.today()

        # Create and activate contract
        contract_data = {
            "name": "One-Time License",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 5000.00,
            "lines": [
                {
                    "description": "Software License",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "ssp_amount": 5000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate
        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )

        # Generate schedules
        response = await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Get schedule
        schedules_response = await client.get(
            f"/api/v1/finance/rev-rec/schedules?organization_id={nonprofit_org.id}&contract_id={contract_id}",
            headers=auth_headers
        )
        schedules = schedules_response.json()["items"]

        schedule = schedules[0]
        assert schedule["recognition_method"] == "point_in_time"
        assert len(schedule["lines"]) == 1  # Single recognition
        assert float(schedule["lines"][0]["amount"]) == 5000.00


# ============================================================================
# REVENUE RECOGNITION RUN TESTS
# ============================================================================

class TestRevRecRun:
    """Test revenue recognition posting."""

    @pytest.mark.asyncio
    async def test_rev_rec_run_dry_run(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test dry run of revenue recognition."""
        today = date.today()

        # Create point-in-time contract (recognizes immediately)
        contract_data = {
            "name": "Immediate Recognition",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "License",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate and generate schedule
        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )

        # Dry run
        response = await client.post(
            f"/api/v1/finance/rev-rec/run?organization_id={nonprofit_org.id}",
            json={
                "as_of_date": str(today),
                "dry_run": True
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lines_processed"] >= 1
        assert float(data["total_amount"]) == 1000.00
        assert data["journal_entries_created"] == 0  # Dry run, no actual entries

    @pytest.mark.asyncio
    async def test_rev_rec_run_actual_post(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test actual revenue recognition posting with journal entries."""
        today = date.today()

        # Create point-in-time contract
        contract_data = {
            "name": "Recognition Test",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 2500.00,
            "lines": [
                {
                    "description": "Professional Service",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 2500.00,
                    "ssp_amount": 2500.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate and generate schedule
        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )

        # Actual run
        response = await client.post(
            f"/api/v1/finance/rev-rec/run?organization_id={nonprofit_org.id}",
            json={
                "as_of_date": str(today),
                "dry_run": False
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lines_posted"] >= 1
        assert data["journal_entries_created"] >= 1
        assert len(data["journal_entry_ids"]) >= 1

    @pytest.mark.asyncio
    async def test_get_due_lines(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test getting lines due for recognition."""
        today = date.today()

        # Create contract
        contract_data = {
            "name": "Due Lines Test",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "Service",
                    "recognition_pattern": "point_in_time",
                    "start_date": str(today),
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Activate and generate schedule
        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )

        # Get due lines
        response = await client.get(
            f"/api/v1/finance/rev-rec/due-lines?organization_id={nonprofit_org.id}&as_of_date={today}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1


# ============================================================================
# WATERFALL REPORT TESTS
# ============================================================================

class TestWaterfallReport:
    """Test revenue waterfall reporting."""

    @pytest.mark.asyncio
    async def test_waterfall_empty(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization
    ):
        """Test waterfall report with no data."""
        today = date.today()
        from_date = today.replace(day=1)
        to_date = (from_date + timedelta(days=365)).replace(day=1) - timedelta(days=1)

        response = await client.get(
            f"/api/v1/finance/rev-rec/waterfall?organization_id={nonprofit_org.id}"
            f"&from_date={from_date}&to_date={to_date}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert float(data["total_planned"]) == 0
        assert float(data["total_posted"]) == 0

    @pytest.mark.asyncio
    async def test_waterfall_with_schedules(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test waterfall report with scheduled revenue."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 12, 31)

        # Create and activate contract
        contract_data = {
            "name": "Waterfall Test",
            "customer_contact_id": customer_contact.id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_transaction_price": 12000.00,
            "lines": [
                {
                    "description": "Service",
                    "recognition_pattern": "straight_line",
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "quantity": 1,
                    "unit_price": 12000.00,
                    "ssp_amount": 12000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        await client.post(
            f"/api/v1/finance/rev-rec/generate-schedules?organization_id={nonprofit_org.id}",
            json={"contract_id": contract_id},
            headers=auth_headers
        )

        # Get waterfall
        response = await client.get(
            f"/api/v1/finance/rev-rec/waterfall?organization_id={nonprofit_org.id}"
            f"&from_date={start_date}&to_date={end_date}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["periods"]) == 12  # 12 months
        assert float(data["total_planned"]) == 12000.00


# ============================================================================
# EDITION GUARD TESTS
# ============================================================================

class TestEditionGuard:
    """Test that features are properly gated by edition."""

    @pytest.mark.asyncio
    async def test_contracts_blocked_for_startup_edition(
        self, client: AsyncClient, auth_headers: dict, startup_org: Organization
    ):
        """Test that contracts endpoint returns 403 for startup edition."""
        response = await client.get(
            f"/api/v1/finance/contracts?organization_id={startup_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "contracts" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rev_rec_blocked_for_startup_edition(
        self, client: AsyncClient, auth_headers: dict, startup_org: Organization
    ):
        """Test that rev rec endpoint returns 403 for startup edition."""
        response = await client.get(
            f"/api/v1/finance/rev-rec/schedules?organization_id={startup_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 403
        assert "revenue recognition" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_contracts_allowed_for_nonprofit_edition(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization
    ):
        """Test that contracts endpoint works for nonprofit edition."""
        response = await client.get(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rev_rec_allowed_for_nonprofit_edition(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization
    ):
        """Test that rev rec endpoint works for nonprofit edition."""
        response = await client.get(
            f"/api/v1/finance/rev-rec/schedules?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_cannot_delete_active_contract(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact, revenue_account: Account, deferred_revenue_account: Account
    ):
        """Test that active contracts cannot be deleted."""
        today = date.today()

        # Create and activate contract
        contract_data = {
            "name": "Active Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "ssp_amount": 1000.00,
                    "revenue_account_id": revenue_account.id,
                    "deferred_revenue_account_id": deferred_revenue_account.id
                }
            ]
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )

        # Try to delete
        response = await client.delete(
            f"/api/v1/finance/contracts/{contract_id}?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_activate_contract_without_lines(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization,
        customer_contact: Contact
    ):
        """Test that contracts without lines cannot be activated."""
        today = date.today()

        # Create contract without lines
        contract_data = {
            "name": "Empty Contract",
            "customer_contact_id": customer_contact.id,
            "start_date": str(today),
            "total_transaction_price": 1000.00,
            "lines": []
        }

        create_response = await client.post(
            f"/api/v1/finance/contracts?organization_id={nonprofit_org.id}",
            json=contract_data,
            headers=auth_headers
        )
        contract_id = create_response.json()["id"]

        # Try to activate
        response = await client.post(
            f"/api/v1/finance/contracts/{contract_id}/activate?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_contract_not_found(
        self, client: AsyncClient, auth_headers: dict, nonprofit_org: Organization
    ):
        """Test 404 for non-existent contract."""
        response = await client.get(
            f"/api/v1/finance/contracts/nonexistent123?organization_id={nonprofit_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404
