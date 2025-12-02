"""
Tests for CRM module (Leads, Opportunities, Activities).

Tests cover:
- CRUD operations for leads, opportunities, activities
- Stage transition validation for opportunities
- Role enforcement (viewer vs member vs admin)
- Organization scoping
- Lead conversion to contact/opportunity
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.contact import Contact, ContactType
from app.models.project import Project, ProjectStatus
from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.opportunity import Opportunity, OpportunityStage, OpportunitySource
from app.models.activity import Activity, ActivityType


# ========== Fixtures ==========

@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer user."""
    user = User(
        email="viewer@example.com",
        name="Viewer User",
        password_hash=get_password_hash("ViewerPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession) -> User:
    """Create a member user."""
    user = User(
        email="member@example.com",
        name="Member User",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_membership(
    db_session: AsyncSession, test_org: Organization, viewer_user: User
) -> OrgMembership:
    """Create a viewer membership."""
    membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer_user.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(membership)
    await db_session.flush()
    return membership


@pytest_asyncio.fixture
async def member_membership(
    db_session: AsyncSession, test_org: Organization, member_user: User
) -> OrgMembership:
    """Create a member membership."""
    membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member_user.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(membership)
    await db_session.flush()
    return membership


@pytest_asyncio.fixture
async def viewer_headers(viewer_user: User) -> dict:
    """Create auth headers for viewer user."""
    token = create_access_token(subject=viewer_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def member_headers(member_user: User) -> dict:
    """Create auth headers for member user."""
    token = create_access_token(subject=member_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_lead(
    db_session: AsyncSession, test_org: Organization, test_user: User
) -> Lead:
    """Create a test lead."""
    lead = Lead(
        organization_id=test_org.id,
        name="Test Lead",
        contact_name="John Lead",
        email="lead@example.com",
        phone="+1234567890",
        company="Lead Corp",
        website="https://leadcorp.com",
        status=LeadStatus.NEW,
        source=LeadSource.WEBSITE,
        owner_user_id=test_user.id,
        notes="Interested in our services",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(lead)
    await db_session.flush()
    return lead


@pytest_asyncio.fixture
async def test_opportunity(
    db_session: AsyncSession, test_org: Organization, test_user: User
) -> Opportunity:
    """Create a test opportunity."""
    opportunity = Opportunity(
        organization_id=test_org.id,
        title="Test Opportunity",
        description="A great sales opportunity",
        amount=Decimal("10000.00"),
        currency="USD",
        stage=OpportunityStage.PROSPECTING,
        probability=10,
        source=OpportunitySource.REFERRAL,
        owner_user_id=test_user.id,
        expected_close_date=date.today() + timedelta(days=30),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(opportunity)
    await db_session.flush()
    return opportunity


@pytest_asyncio.fixture
async def test_activity(
    db_session: AsyncSession, test_org: Organization, test_opportunity: Opportunity, test_user: User
) -> Activity:
    """Create a test activity."""
    activity = Activity(
        organization_id=test_org.id,
        opportunity_id=test_opportunity.id,
        type=ActivityType.CALL,
        subject="Follow-up call",
        description="Discussed pricing options",
        created_by_user_id=test_user.id,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(activity)
    await db_session.flush()
    return activity


# ========== Lead Tests ==========

class TestLeadsCRUD:
    """Test Lead CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_leads_empty(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test listing leads when organization has none."""
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["totalItems"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_leads_with_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test listing leads when organization has one."""
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test Lead"
        assert data["items"][0]["status"] == "new"

    @pytest.mark.asyncio
    async def test_create_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating a new lead."""
        lead_data = {
            "name": "New Lead",
            "contact_name": "Jane Lead",
            "email": "jane@example.com",
            "phone": "+1987654321",
            "company": "New Company",
            "status": "new",
            "source": "referral"
        }
        response = await client.post(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            json=lead_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Lead"
        assert data["email"] == "jane@example.com"
        assert data["status"] == "new"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test getting a single lead."""
        response = await client.get(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_lead.id
        assert data["name"] == "Test Lead"

    @pytest.mark.asyncio
    async def test_get_lead_not_found(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test getting a non-existent lead."""
        response = await client.get(
            f"/api/v1/crm/leads/nonexistent123?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test updating a lead."""
        update_data = {
            "name": "Updated Lead Name",
            "status": "contacted"
        }
        response = await client.patch(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Lead Name"
        assert data["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_delete_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test deleting a lead (as admin/owner)."""
        response = await client.delete(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        response = await client.get(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestLeadConversion:
    """Test Lead conversion to Contact/Opportunity."""

    @pytest.mark.asyncio
    async def test_convert_lead_to_contact(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test converting a lead to a contact."""
        convert_data = {
            "create_contact": True,
            "create_opportunity": False
        }
        response = await client.post(
            f"/api/v1/crm/leads/{test_lead.id}/convert?organization_id={test_org.id}",
            json=convert_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "converted"
        assert data["converted_contact_id"] is not None
        assert data["converted_opportunity_id"] is None

    @pytest.mark.asyncio
    async def test_convert_lead_to_contact_and_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test converting a lead to both contact and opportunity."""
        convert_data = {
            "create_contact": True,
            "create_opportunity": True,
            "opportunity_title": "Deal from Lead",
            "opportunity_amount": 25000.00
        }
        response = await client.post(
            f"/api/v1/crm/leads/{test_lead.id}/convert?organization_id={test_org.id}",
            json=convert_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "converted"
        assert data["converted_contact_id"] is not None
        assert data["converted_opportunity_id"] is not None

    @pytest.mark.asyncio
    async def test_convert_already_converted_lead(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead, db_session: AsyncSession
    ):
        """Test that converting an already converted lead fails."""
        # First conversion
        convert_data = {"create_contact": True, "create_opportunity": False}
        response = await client.post(
            f"/api/v1/crm/leads/{test_lead.id}/convert?organization_id={test_org.id}",
            json=convert_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        # Second conversion attempt
        response = await client.post(
            f"/api/v1/crm/leads/{test_lead.id}/convert?organization_id={test_org.id}",
            json=convert_data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "already been converted" in response.json()["detail"]


# ========== Opportunity Tests ==========

class TestOpportunitiesCRUD:
    """Test Opportunity CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_opportunities_empty(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test listing opportunities when organization has none."""
        response = await client.get(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_list_opportunities_with_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test listing opportunities when organization has one."""
        response = await client.get(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert data["items"][0]["title"] == "Test Opportunity"

    @pytest.mark.asyncio
    async def test_create_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization
    ):
        """Test creating a new opportunity."""
        opp_data = {
            "title": "New Opportunity",
            "description": "A new sales opportunity",
            "amount": 50000.00,
            "stage": "prospecting",
            "source": "web"
        }
        response = await client.post(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}",
            json=opp_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Opportunity"
        assert data["stage"] == "prospecting"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test getting a single opportunity."""
        response = await client.get(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_opportunity.id
        assert data["title"] == "Test Opportunity"

    @pytest.mark.asyncio
    async def test_update_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test updating an opportunity."""
        update_data = {
            "title": "Updated Opportunity",
            "amount": 15000.00
        }
        response = await client.patch(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Opportunity"

    @pytest.mark.asyncio
    async def test_delete_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test deleting an opportunity (as admin/owner)."""
        response = await client.delete(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


class TestOpportunityStageTransitions:
    """Test Opportunity stage transition validation."""

    @pytest.mark.asyncio
    async def test_valid_stage_transition_prospecting_to_qualification(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test valid transition from prospecting to qualification."""
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "qualification"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "qualification"
        assert data["probability"] == 25

    @pytest.mark.asyncio
    async def test_valid_stage_transition_to_lost(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test valid transition from prospecting to lost."""
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "lost"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "lost"
        assert data["probability"] == 0
        assert data["actual_close_date"] is not None

    @pytest.mark.asyncio
    async def test_invalid_stage_transition_prospecting_to_won(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test invalid transition from prospecting directly to won."""
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "won"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot transition" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_stage_transition_prospecting_to_negotiation(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test invalid transition from prospecting directly to negotiation."""
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "negotiation"},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Cannot transition" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_full_pipeline_to_won(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test moving an opportunity through the full pipeline to won."""
        stages = ["qualification", "proposal_made", "negotiation", "won"]
        for stage in stages:
            response = await client.post(
                f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
                json={"new_stage": stage},
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed to transition to {stage}"
            assert response.json()["stage"] == stage

        # Verify final state
        final = response.json()
        assert final["probability"] == 100
        assert final["actual_close_date"] is not None

    @pytest.mark.asyncio
    async def test_reopen_lost_opportunity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test reopening a lost opportunity back to prospecting."""
        # First, move to lost
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "lost"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "lost"

        # Reopen to prospecting
        response = await client.post(
            f"/api/v1/crm/opportunities/{test_opportunity.id}/stage?organization_id={test_org.id}",
            json={"new_stage": "prospecting"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "prospecting"
        assert data["actual_close_date"] is None


# ========== Activity Tests ==========

class TestActivitiesCRUD:
    """Test Activity CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_activities(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization,
        test_opportunity: Opportunity, test_activity: Activity
    ):
        """Test listing activities for an opportunity."""
        response = await client.get(
            f"/api/v1/crm/activities?organization_id={test_org.id}&opportunity_id={test_opportunity.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 1
        assert data["items"][0]["subject"] == "Follow-up call"

    @pytest.mark.asyncio
    async def test_create_activity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test creating a new activity."""
        activity_data = {
            "opportunity_id": test_opportunity.id,
            "type": "meeting",
            "subject": "Client meeting",
            "description": "Demo presentation"
        }
        response = await client.post(
            f"/api/v1/crm/activities?organization_id={test_org.id}",
            json=activity_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "Client meeting"
        assert data["type"] == "meeting"

    @pytest.mark.asyncio
    async def test_create_task_activity_with_due_date(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test creating a task activity with due date."""
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        activity_data = {
            "opportunity_id": test_opportunity.id,
            "type": "task",
            "subject": "Send proposal",
            "due_date": due_date
        }
        response = await client.post(
            f"/api/v1/crm/activities?organization_id={test_org.id}",
            json=activity_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "task"
        assert data["due_date"] is not None

    @pytest.mark.asyncio
    async def test_get_activity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_activity: Activity
    ):
        """Test getting a single activity."""
        response = await client.get(
            f"/api/v1/crm/activities/{test_activity.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_activity.id

    @pytest.mark.asyncio
    async def test_update_activity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_activity: Activity
    ):
        """Test updating an activity."""
        update_data = {
            "subject": "Updated subject",
            "description": "Updated description"
        }
        response = await client.patch(
            f"/api/v1/crm/activities/{test_activity.id}?organization_id={test_org.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Updated subject"

    @pytest.mark.asyncio
    async def test_complete_activity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_activity: Activity
    ):
        """Test completing an activity (marking as done)."""
        response = await client.post(
            f"/api/v1/crm/activities/{test_activity.id}/complete?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_delete_activity(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_activity: Activity
    ):
        """Test deleting an activity (as admin/owner)."""
        response = await client.delete(
            f"/api/v1/crm/activities/{test_activity.id}?organization_id={test_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 204


# ========== Role Enforcement Tests ==========

class TestCRMRoleEnforcement:
    """Test role-based access control for CRM module."""

    @pytest.mark.asyncio
    async def test_viewer_can_list_leads(
        self, client: AsyncClient, viewer_headers: dict, viewer_membership, test_org: Organization, test_lead: Lead
    ):
        """Test that viewer role can list leads."""
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            headers=viewer_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_lead(
        self, client: AsyncClient, viewer_headers: dict, viewer_membership, test_org: Organization
    ):
        """Test that viewer role cannot create leads."""
        lead_data = {"name": "New Lead", "status": "new", "source": "website"}
        response = await client.post(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            json=lead_data,
            headers=viewer_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_can_create_lead(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization
    ):
        """Test that member role can create leads."""
        lead_data = {"name": "New Lead", "status": "new", "source": "website"}
        response = await client.post(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            json=lead_data,
            headers=member_headers
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_member_cannot_delete_lead(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization, test_lead: Lead
    ):
        """Test that member role cannot delete leads (requires admin)."""
        response = await client.delete(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={test_org.id}",
            headers=member_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_opportunity(
        self, client: AsyncClient, viewer_headers: dict, viewer_membership, test_org: Organization
    ):
        """Test that viewer role cannot create opportunities."""
        opp_data = {"title": "New Opp", "stage": "prospecting", "source": "web"}
        response = await client.post(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}",
            json=opp_data,
            headers=viewer_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_can_create_opportunity(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization
    ):
        """Test that member role can create opportunities."""
        opp_data = {"title": "New Opp", "stage": "prospecting", "source": "web"}
        response = await client.post(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}",
            json=opp_data,
            headers=member_headers
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_member_cannot_delete_opportunity(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test that member role cannot delete opportunities (requires admin)."""
        response = await client.delete(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={test_org.id}",
            headers=member_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_can_update_own_opportunity(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization, member_user: User, db_session: AsyncSession
    ):
        """Test that member can update their own opportunities."""
        # Create opportunity owned by member
        opportunity = Opportunity(
            organization_id=test_org.id,
            title="Member's Opportunity",
            stage=OpportunityStage.PROSPECTING,
            source=OpportunitySource.WEB,
            owner_user_id=member_user.id,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(opportunity)
        await db_session.flush()

        response = await client.patch(
            f"/api/v1/crm/opportunities/{opportunity.id}?organization_id={test_org.id}",
            json={"title": "Updated Title"},
            headers=member_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_member_cannot_update_others_opportunity(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test that member cannot update opportunities owned by others."""
        response = await client.patch(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={test_org.id}",
            json={"title": "Hacked Title"},
            headers=member_headers
        )
        assert response.status_code == 403
        assert "your own" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_activity(
        self, client: AsyncClient, viewer_headers: dict, viewer_membership, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test that viewer role cannot create activities."""
        activity_data = {
            "opportunity_id": test_opportunity.id,
            "type": "call",
            "subject": "Test call"
        }
        response = await client.post(
            f"/api/v1/crm/activities?organization_id={test_org.id}",
            json=activity_data,
            headers=viewer_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_cannot_delete_activity(
        self, client: AsyncClient, member_headers: dict, member_membership, test_org: Organization, test_activity: Activity
    ):
        """Test that member role cannot delete activities (requires admin)."""
        response = await client.delete(
            f"/api/v1/crm/activities/{test_activity.id}?organization_id={test_org.id}",
            headers=member_headers
        )
        assert response.status_code == 403


# ========== Organization Scoping Tests ==========

class TestCRMOrganizationScoping:
    """Test that CRM data is properly scoped by organization."""

    @pytest.mark.asyncio
    async def test_lead_isolated_by_organization(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead, db_session: AsyncSession, test_user: User
    ):
        """Test that leads are isolated by organization."""
        # Create another organization
        other_org = Organization(
            name="Other Organization",
            description="Another org for testing",
            owner_id=test_user.id,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(other_org)
        await db_session.flush()

        # Create membership for other org
        other_membership = OrgMembership(
            organization_id=other_org.id,
            user_id=test_user.id,
            role=OrgMembershipRole.OWNER,
            is_active=True,
            joined_at=datetime.now(timezone.utc),
        )
        db_session.add(other_membership)
        await db_session.flush()

        # List leads for other org should be empty
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={other_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 0

        # Lead should not be accessible from other org
        response = await client.get(
            f"/api/v1/crm/leads/{test_lead.id}?organization_id={other_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_opportunity_isolated_by_organization(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity, db_session: AsyncSession, test_user: User
    ):
        """Test that opportunities are isolated by organization."""
        # Create another organization
        other_org = Organization(
            name="Other Organization 2",
            description="Another org",
            owner_id=test_user.id,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(other_org)
        await db_session.flush()

        # Create membership for other org
        other_membership = OrgMembership(
            organization_id=other_org.id,
            user_id=test_user.id,
            role=OrgMembershipRole.OWNER,
            is_active=True,
            joined_at=datetime.now(timezone.utc),
        )
        db_session.add(other_membership)
        await db_session.flush()

        # Opportunity should not be accessible from other org
        response = await client.get(
            f"/api/v1/crm/opportunities/{test_opportunity.id}?organization_id={other_org.id}",
            headers=auth_headers
        )
        assert response.status_code == 404


# ========== Search and Filter Tests ==========

class TestCRMSearchAndFilters:
    """Test search and filter functionality."""

    @pytest.mark.asyncio
    async def test_search_leads_by_name(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test searching leads by name."""
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}&search=Test",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_filter_leads_by_status(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_lead: Lead
    ):
        """Test filtering leads by status."""
        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}&status=new",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 1

        response = await client.get(
            f"/api/v1/crm/leads?organization_id={test_org.id}&status=contacted",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 0

    @pytest.mark.asyncio
    async def test_filter_opportunities_by_stage(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity
    ):
        """Test filtering opportunities by stage."""
        response = await client.get(
            f"/api/v1/crm/opportunities?organization_id={test_org.id}&stage=prospecting",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 1

    @pytest.mark.asyncio
    async def test_filter_activities_by_type(
        self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_opportunity: Opportunity, test_activity: Activity
    ):
        """Test filtering activities by type."""
        response = await client.get(
            f"/api/v1/crm/activities?organization_id={test_org.id}&type=call",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 1

        response = await client.get(
            f"/api/v1/crm/activities?organization_id={test_org.id}&type=meeting",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["totalItems"] == 0


# ========== Authentication Tests ==========

class TestCRMAuthentication:
    """Test authentication requirements for CRM endpoints."""

    @pytest.mark.asyncio
    async def test_list_leads_unauthorized(self, client: AsyncClient, test_org: Organization):
        """Test listing leads without authentication."""
        response = await client.get(f"/api/v1/crm/leads?organization_id={test_org.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_opportunities_unauthorized(self, client: AsyncClient, test_org: Organization):
        """Test listing opportunities without authentication."""
        response = await client.get(f"/api/v1/crm/opportunities?organization_id={test_org.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_activities_unauthorized(self, client: AsyncClient, test_org: Organization):
        """Test listing activities without authentication."""
        response = await client.get(f"/api/v1/crm/activities?organization_id={test_org.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_lead_unauthorized(self, client: AsyncClient, test_org: Organization):
        """Test creating lead without authentication."""
        response = await client.post(
            f"/api/v1/crm/leads?organization_id={test_org.id}",
            json={"name": "Test", "status": "new", "source": "website"}
        )
        assert response.status_code == 401
