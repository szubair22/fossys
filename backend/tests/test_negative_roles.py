"""Negative authorization tests for role enforcement.
Validates that viewer or insufficient roles cannot perform protected mutations.
"""
import os
from datetime import datetime, timezone
import os
import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.core.config import settings

# Ensure writable upload dir for tests (mirror approach in test_files.py)
settings.UPLOAD_DIR = os.path.abspath("./test_uploads")
from app.db.base import Base


@pytest.mark.asyncio
async def test_file_upload_viewer_forbidden(client: AsyncClient, db_session, test_org):
    """Viewer membership should not be able to upload a file (requires member)."""
    # Create viewer user + membership
    viewer = User(
        email="viewer@example.com",
        name="Viewer User",
        password_hash=get_password_hash("ViewerPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(viewer)
    await db_session.flush()
    viewer_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(viewer_membership)
    await db_session.flush()

    token = create_access_token(subject=viewer.id)
    headers = {"Authorization": f"Bearer {token}"}

    files = {"upload": ("denied.txt", b"Nope", "text/plain")}
    data = {
        "organization": test_org.id,
        "name": "denied.txt",
        "description": "Should be forbidden",
    }
    resp = await client.post(
        "/api/collections/files/records",
        headers=headers,
        files=files,
        data=data,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_file_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member can upload but cannot delete (requires admin)."""
    # Upload as owner (auth_headers fixture corresponds to owner membership via test_user)
    files = {"upload": ("owned.txt", b"Owned Content", "text/plain")}
    data = {"organization": test_org.id, "name": "owned.txt"}
    up_resp = await client.post(
        "/api/collections/files/records",
        headers=auth_headers,
        files=files,
        data=data,
    )
    assert up_resp.status_code == 200, up_resp.text
    file_id = up_resp.json()["id"]

    # Create member user
    member = User(
        email="member@example.com",
        name="Member User",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    member_token = create_access_token(subject=member.id)
    member_headers = {"Authorization": f"Bearer {member_token}"}

    del_resp = await client.delete(
        f"/api/collections/files/records/{file_id}",
        headers=member_headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_minutes_create_viewer_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Viewer should not be able to create meeting minutes (requires meeting admin + org admin)."""
    # Create a meeting as owner
    meeting_payload = {
        "title": "Test Meeting",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "organization": test_org.id,
    }
    meeting_resp = await client.post(
        "/api/collections/meetings/records",
        headers=auth_headers,
        json=meeting_payload,
    )
    assert meeting_resp.status_code == 200, meeting_resp.text
    meeting_id = meeting_resp.json()["id"]

    # Create viewer user + membership
    viewer2 = User(
        email="viewer2@example.com",
        name="Viewer Two",
        password_hash=get_password_hash("Viewer2Pass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(viewer2)
    await db_session.flush()
    viewer2_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer2.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(viewer2_membership)
    await db_session.flush()

    v2_token = create_access_token(subject=viewer2.id)
    v2_headers = {"Authorization": f"Bearer {v2_token}"}

    minutes_payload = {
        "meeting_id": meeting_id,
        "content": "Minutes attempt",
        "status": "draft"
    }

    create_resp = await client.post(
        "/api/v1/governance/minutes",
        headers=v2_headers,
        json=minutes_payload,
    )
    assert create_resp.status_code == 403, create_resp.text


@pytest.mark.asyncio
async def test_contact_create_viewer_forbidden(client: AsyncClient, db_session, test_org):
    """Viewer should not be able to create contacts (requires admin)."""
    viewer = User(
        email="viewer_contact@example.com",
        name="Viewer Contact",
        password_hash=get_password_hash("ViewerPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(viewer)
    await db_session.flush()
    viewer_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(viewer_membership)
    await db_session.flush()

    token = create_access_token(subject=viewer.id)
    headers = {"Authorization": f"Bearer {token}"}

    contact_payload = {
        "name": "Test Contact",
        "email": "contact@test.com",
    }
    resp = await client.post(
        f"/api/v1/membership/contacts?organization_id={test_org.id}",
        headers=headers,
        json=contact_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_contact_create_member_forbidden(client: AsyncClient, db_session, test_org):
    """Member should not be able to create contacts (requires admin)."""
    member = User(
        email="member_contact@example.com",
        name="Member Contact",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    contact_payload = {
        "name": "Test Contact",
        "email": "contact@test.com",
    }
    resp = await client.post(
        f"/api/v1/membership/contacts?organization_id={test_org.id}",
        headers=headers,
        json=contact_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_member_create_viewer_forbidden(client: AsyncClient, db_session, test_org):
    """Viewer should not be able to create members (requires admin)."""
    viewer = User(
        email="viewer_member@example.com",
        name="Viewer Member",
        password_hash=get_password_hash("ViewerPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(viewer)
    await db_session.flush()
    viewer_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(viewer_membership)
    await db_session.flush()

    token = create_access_token(subject=viewer.id)
    headers = {"Authorization": f"Bearer {token}"}

    member_payload = {
        "name": "Test Member",
        "email": "testmember@test.com",
        "status": "active",
        "member_type": "regular",
    }
    resp = await client.post(
        f"/api/v1/membership/members?organization_id={test_org.id}",
        headers=headers,
        json=member_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_member_create_member_forbidden(client: AsyncClient, db_session, test_org):
    """Member role should not be able to create members (requires admin)."""
    member = User(
        email="member_member@example.com",
        name="Member Member",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    member_payload = {
        "name": "Test Member",
        "email": "testmember2@test.com",
        "status": "active",
        "member_type": "regular",
    }
    resp = await client.post(
        f"/api/v1/membership/members?organization_id={test_org.id}",
        headers=headers,
        json=member_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_account_create_viewer_forbidden(client: AsyncClient, db_session, test_org):
    """Viewer should not be able to create accounts (requires admin)."""
    viewer = User(
        email="viewer_account@example.com",
        name="Viewer Account",
        password_hash=get_password_hash("ViewerPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(viewer)
    await db_session.flush()
    viewer_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=viewer.id,
        role=OrgMembershipRole.VIEWER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(viewer_membership)
    await db_session.flush()

    token = create_access_token(subject=viewer.id)
    headers = {"Authorization": f"Bearer {token}"}

    account_payload = {
        "code": "1001",
        "name": "Test Account",
        "account_type": "asset",
    }
    resp = await client.post(
        f"/api/v1/finance/accounts?organization_id={test_org.id}",
        headers=headers,
        json=account_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_account_create_member_forbidden(client: AsyncClient, db_session, test_org):
    """Member should not be able to create accounts (requires admin)."""
    member = User(
        email="member_account@example.com",
        name="Member Account",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    account_payload = {
        "code": "1002",
        "name": "Test Account",
        "account_type": "asset",
    }
    resp = await client.post(
        f"/api/v1/finance/accounts?organization_id={test_org.id}",
        headers=headers,
        json=account_payload,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_journal_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete journal entries (requires admin)."""
    from app.models.journal_entry import JournalEntry, JournalEntryStatus
    from datetime import date as dt_date
    from app.core.security import verify_token

    # Get the test user ID from auth_headers fixture
    test_user_token = auth_headers["Authorization"].replace("Bearer ", "")
    test_user_id = verify_token(test_user_token)

    # Create journal entry as owner/admin
    entry = JournalEntry(
        organization_id=test_org.id,
        entry_number="JE-000001",
        entry_date=dt_date.today(),
        description="Test Journal Entry",
        status=JournalEntryStatus.DRAFT,
        created_by_id=test_user_id,
    )
    db_session.add(entry)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_journal@example.com",
        name="Member Journal",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/finance/journal-entries/{entry.id}?organization_id={test_org.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_donation_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete donations (requires admin)."""
    from app.models.donation import Donation, DonationStatus
    from datetime import date as dt_date
    from decimal import Decimal

    # Create donation
    donation = Donation(
        organization_id=test_org.id,
        donor_name="Test Donor",
        amount=Decimal("100.00"),
        currency="USD",
        donation_date=dt_date.today(),
        status=DonationStatus.RECEIVED,
    )
    db_session.add(donation)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_donation@example.com",
        name="Member Donation",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/finance/donations/{donation.id}?organization_id={test_org.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_motion_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete motions (requires admin)."""
    from app.models.motion import Motion, MotionWorkflowState
    from app.models.meeting import Meeting, MeetingStatus
    from app.core.security import verify_token

    # Get the test user ID from auth_headers fixture by decoding the token
    test_user_token = auth_headers["Authorization"].replace("Bearer ", "")
    test_user_id = verify_token(test_user_token)

    # Create meeting first
    meeting = Meeting(
        title="Test Meeting For Motion",
        organization_id=test_org.id,
        start_time=datetime.now(timezone.utc),
        status=MeetingStatus.SCHEDULED,
        created_by_id=test_user_id,
    )
    db_session.add(meeting)
    await db_session.flush()

    # Create motion
    motion = Motion(
        meeting_id=meeting.id,
        submitter_id=test_user_id,
        title="Test Motion",
        text="Motion text",
        workflow_state=MotionWorkflowState.DRAFT,
    )
    db_session.add(motion)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_motion@example.com",
        name="Member Motion",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/governance/motions/{motion.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_poll_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete polls (requires admin)."""
    from app.models.poll import Poll, PollStatus
    from app.models.meeting import Meeting, MeetingStatus
    from app.core.security import verify_token

    # Get the test user ID from auth_headers fixture
    test_user_token = auth_headers["Authorization"].replace("Bearer ", "")
    test_user_id = verify_token(test_user_token)

    # Create meeting first
    meeting = Meeting(
        title="Test Meeting For Poll",
        organization_id=test_org.id,
        start_time=datetime.now(timezone.utc),
        status=MeetingStatus.SCHEDULED,
        created_by_id=test_user_id,
    )
    db_session.add(meeting)
    await db_session.flush()

    # Create poll
    from app.models.poll import PollType
    poll = Poll(
        meeting_id=meeting.id,
        title="Test Poll Question",
        poll_type=PollType.YES_NO,
        options=[{"text": "Yes"}, {"text": "No"}],
        status=PollStatus.DRAFT,
        created_by_id=test_user_id,
    )
    db_session.add(poll)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_poll@example.com",
        name="Member Poll",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/governance/polls/{poll.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_agenda_item_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete agenda items (requires admin)."""
    from app.models.agenda_item import AgendaItem, AgendaItemType, AgendaItemStatus
    from app.models.meeting import Meeting, MeetingStatus
    from app.core.security import verify_token

    # Get the test user ID from auth_headers fixture
    test_user_token = auth_headers["Authorization"].replace("Bearer ", "")
    test_user_id = verify_token(test_user_token)

    # Create meeting first
    meeting = Meeting(
        title="Test Meeting For Agenda",
        organization_id=test_org.id,
        start_time=datetime.now(timezone.utc),
        status=MeetingStatus.SCHEDULED,
        created_by_id=test_user_id,
    )
    db_session.add(meeting)
    await db_session.flush()

    # Create agenda item
    agenda_item = AgendaItem(
        meeting_id=meeting.id,
        title="Test Agenda Item",
        item_type=AgendaItemType.TOPIC,
        status=AgendaItemStatus.PENDING,
        order=1,
    )
    db_session.add(agenda_item)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_agenda@example.com",
        name="Member Agenda",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/governance/agenda-items/{agenda_item.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_template_delete_member_forbidden(client: AsyncClient, auth_headers: dict, db_session, test_org):
    """Member should not be able to delete meeting templates (requires admin)."""
    from app.models.meeting_template import MeetingTemplate
    from app.core.security import verify_token

    # Get the test user ID from auth_headers fixture
    test_user_token = auth_headers["Authorization"].replace("Bearer ", "")
    test_user_id = verify_token(test_user_token)

    # Create template
    template = MeetingTemplate(
        name="Test Template",
        organization_id=test_org.id,
        created_by_id=test_user_id,
        is_global=False,
    )
    db_session.add(template)
    await db_session.flush()

    # Create member user
    member = User(
        email="member_template@example.com",
        name="Member Template",
        password_hash=get_password_hash("MemberPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    member_membership = OrgMembership(
        organization_id=test_org.id,
        user_id=member.id,
        role=OrgMembershipRole.MEMBER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member_membership)
    await db_session.flush()

    token = create_access_token(subject=member.id)
    headers = {"Authorization": f"Bearer {token}"}

    del_resp = await client.delete(
        f"/api/v1/governance/templates/{template.id}",
        headers=headers,
    )
    assert del_resp.status_code == 403, del_resp.text


@pytest.mark.asyncio
async def test_unauthenticated_access_forbidden(client: AsyncClient, test_org):
    """Unauthenticated requests should be rejected with 401."""
    # Test various endpoints without auth header
    endpoints = [
        f"/api/v1/governance/org-memberships/my",
        f"/api/v1/membership/members?organization_id={test_org.id}",
        f"/api/v1/membership/contacts?organization_id={test_org.id}",
        f"/api/v1/finance/accounts?organization_id={test_org.id}",
    ]

    for endpoint in endpoints:
        resp = await client.get(endpoint)
        assert resp.status_code == 401, f"Expected 401 for {endpoint}, got {resp.status_code}"
