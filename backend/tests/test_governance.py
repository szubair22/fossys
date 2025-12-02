"""
Tests for the Governance v1 API endpoints.

Tests cover:
- Committees CRUD
- Meetings CRUD
- Participants (Attendance) CRUD
- Agenda Items CRUD
- Motions CRUD and workflow transitions
- Polls CRUD and voting
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from app.models.committee import Committee
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.models.agenda_item import AgendaItem, AgendaItemType, AgendaItemStatus
from app.models.motion import Motion, MotionWorkflowState
from app.models.poll import Poll, PollType, PollStatus
from app.models.vote import Vote


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_committee(db_session: AsyncSession, test_org: Organization, test_user: User) -> Committee:
    """Create a test committee."""
    committee = Committee(
        organization_id=test_org.id,
        name="Test Committee",
        description="A test committee",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    committee.admins = [test_user]
    db_session.add(committee)
    await db_session.flush()
    return committee


@pytest_asyncio.fixture
async def test_meeting(db_session: AsyncSession, test_committee: Committee, test_user: User) -> Meeting:
    """Create a test meeting."""
    meeting = Meeting(
        title="Test Meeting",
        description="A test meeting",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MeetingStatus.SCHEDULED,
        meeting_type=MeetingType.GENERAL,
        committee_id=test_committee.id,
        created_by_id=test_user.id,
        jitsi_room="test-room-123",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(meeting)
    await db_session.flush()

    # Add creator as participant
    participant = Participant(
        meeting_id=meeting.id,
        user_id=test_user.id,
        role=ParticipantRole.ADMIN,
        is_present=False,
        attendance_status=AttendanceStatus.INVITED,
        can_vote=True,
        vote_weight=1,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(participant)
    await db_session.flush()

    return meeting


@pytest_asyncio.fixture
async def test_participant(db_session: AsyncSession, test_meeting: Meeting, test_user: User) -> Participant:
    """Get the test participant created with the meeting."""
    from sqlalchemy import select
    result = await db_session.execute(
        select(Participant).where(
            Participant.meeting_id == test_meeting.id,
            Participant.user_id == test_user.id
        )
    )
    return result.scalar_one()


@pytest_asyncio.fixture
async def test_agenda_item(db_session: AsyncSession, test_meeting: Meeting) -> AgendaItem:
    """Create a test agenda item."""
    item = AgendaItem(
        meeting_id=test_meeting.id,
        title="Test Agenda Item",
        description="Discussion topic",
        order=1,
        duration_minutes=15,
        item_type=AgendaItemType.TOPIC,
        status=AgendaItemStatus.PENDING,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(item)
    await db_session.flush()
    return item


@pytest_asyncio.fixture
async def test_motion(db_session: AsyncSession, test_meeting: Meeting, test_user: User, test_agenda_item: AgendaItem) -> Motion:
    """Create a test motion."""
    motion = Motion(
        meeting_id=test_meeting.id,
        agenda_item_id=test_agenda_item.id,
        number="M-001",
        title="Test Motion",
        text="Be it resolved that this is a test motion.",
        reason="For testing purposes",
        submitter_id=test_user.id,
        workflow_state=MotionWorkflowState.DRAFT,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(motion)
    await db_session.flush()
    return motion


@pytest_asyncio.fixture
async def test_poll(db_session: AsyncSession, test_meeting: Meeting, test_user: User) -> Poll:
    """Create a test poll."""
    poll = Poll(
        meeting_id=test_meeting.id,
        title="Test Poll",
        description="A test poll",
        poll_type=PollType.YES_NO,
        status=PollStatus.DRAFT,
        anonymous=False,
        created_by_id=test_user.id,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(poll)
    await db_session.flush()
    return poll


# ============================================================================
# COMMITTEE TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestCommittees:
    """Tests for Committees v1 API."""

    async def test_create_committee(self, client: AsyncClient, auth_headers: dict, test_org: Organization):
        """Test creating a committee."""
        response = await client.post(
            f"/api/v1/governance/committees?organization_id={test_org.id}",
            json={
                "organization_id": test_org.id,
                "name": "New Committee",
                "description": "A new committee",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Committee"
        assert data["organization_id"] == test_org.id

    async def test_list_committees(self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_committee: Committee):
        """Test listing committees."""
        response = await client.get(
            f"/api/v1/governance/committees?organization_id={test_org.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1
        assert len(data["items"]) >= 1

    async def test_get_committee(self, client: AsyncClient, auth_headers: dict, test_committee: Committee):
        """Test getting a committee."""
        response = await client.get(
            f"/api/v1/governance/committees/{test_committee.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_committee.id
        assert data["name"] == test_committee.name

    async def test_update_committee(self, client: AsyncClient, auth_headers: dict, test_committee: Committee):
        """Test updating a committee."""
        response = await client.patch(
            f"/api/v1/governance/committees/{test_committee.id}",
            json={"name": "Updated Committee Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Committee Name"

    async def test_delete_committee(self, client: AsyncClient, auth_headers: dict, test_org: Organization, test_user: User, db_session: AsyncSession):
        """Test deleting a committee."""
        # Create a committee to delete
        committee = Committee(
            organization_id=test_org.id,
            name="Committee to Delete",
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        committee.admins = [test_user]
        db_session.add(committee)
        await db_session.flush()

        response = await client.delete(
            f"/api/v1/governance/committees/{committee.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204


# ============================================================================
# MEETING TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestMeetings:
    """Tests for Meetings v1 API."""

    async def test_create_meeting(self, client: AsyncClient, auth_headers: dict, test_committee: Committee):
        """Test creating a meeting."""
        start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = await client.post(
            "/api/v1/governance/meetings",
            json={
                "title": "New Meeting",
                "description": "A new meeting",
                "start_time": start_time,
                "status": "scheduled",
                "meeting_type": "general",
                "committee_id": test_committee.id,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Meeting"
        assert data["jitsi_room"] is not None

    async def test_list_meetings(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test listing meetings."""
        response = await client.get(
            "/api/v1/governance/meetings",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_get_meeting(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test getting a meeting."""
        response = await client.get(
            f"/api/v1/governance/meetings/{test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_meeting.id

    async def test_update_meeting(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test updating a meeting."""
        response = await client.patch(
            f"/api/v1/governance/meetings/{test_meeting.id}",
            json={"title": "Updated Meeting Title"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Meeting Title"

    async def test_close_meeting(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test closing a meeting."""
        response = await client.post(
            f"/api/v1/governance/meetings/{test_meeting.id}/close",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    async def test_reopen_meeting(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting, db_session: AsyncSession):
        """Test reopening a closed meeting."""
        # First close the meeting
        test_meeting.status = MeetingStatus.COMPLETED
        await db_session.flush()

        response = await client.post(
            f"/api/v1/governance/meetings/{test_meeting.id}/reopen",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"


# ============================================================================
# PARTICIPANT TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestParticipants:
    """Tests for Participants v1 API."""

    async def test_list_participants(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting, test_participant: Participant):
        """Test listing participants."""
        response = await client.get(
            f"/api/v1/governance/participants?meeting_id={test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_get_participant(self, client: AsyncClient, auth_headers: dict, test_participant: Participant):
        """Test getting a participant."""
        response = await client.get(
            f"/api/v1/governance/participants/{test_participant.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_participant.id

    async def test_update_participant_attendance(self, client: AsyncClient, auth_headers: dict, test_participant: Participant):
        """Test updating participant attendance."""
        response = await client.patch(
            f"/api/v1/governance/participants/{test_participant.id}",
            json={"attendance_status": "present"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["attendance_status"] == "present"
        assert data["is_present"] == True

    async def test_mark_present(self, client: AsyncClient, auth_headers: dict, test_participant: Participant):
        """Test marking participant as present."""
        response = await client.post(
            f"/api/v1/governance/participants/{test_participant.id}/mark-present",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["attendance_status"] == "present"

    async def test_mark_absent(self, client: AsyncClient, auth_headers: dict, test_participant: Participant, db_session: AsyncSession):
        """Test marking participant as absent."""
        # First mark as present
        test_participant.attendance_status = AttendanceStatus.PRESENT
        test_participant.is_present = True
        await db_session.flush()

        response = await client.post(
            f"/api/v1/governance/participants/{test_participant.id}/mark-absent",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["attendance_status"] == "absent"


# ============================================================================
# AGENDA ITEM TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestAgendaItems:
    """Tests for Agenda Items v1 API."""

    async def test_create_agenda_item(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test creating an agenda item."""
        response = await client.post(
            "/api/v1/governance/agenda-items",
            json={
                "meeting_id": test_meeting.id,
                "title": "New Agenda Item",
                "description": "Discussion topic",
                "duration_minutes": 10,
                "item_type": "topic",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Agenda Item"

    async def test_list_agenda_items(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting, test_agenda_item: AgendaItem):
        """Test listing agenda items."""
        response = await client.get(
            f"/api/v1/governance/agenda-items?meeting_id={test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_update_agenda_item(self, client: AsyncClient, auth_headers: dict, test_agenda_item: AgendaItem):
        """Test updating an agenda item."""
        response = await client.patch(
            f"/api/v1/governance/agenda-items/{test_agenda_item.id}",
            json={"title": "Updated Agenda Item"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Agenda Item"

    async def test_start_agenda_item(self, client: AsyncClient, auth_headers: dict, test_agenda_item: AgendaItem):
        """Test starting an agenda item."""
        response = await client.post(
            f"/api/v1/governance/agenda-items/{test_agenda_item.id}/start",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    async def test_complete_agenda_item(self, client: AsyncClient, auth_headers: dict, test_agenda_item: AgendaItem):
        """Test completing an agenda item."""
        response = await client.post(
            f"/api/v1/governance/agenda-items/{test_agenda_item.id}/complete",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


# ============================================================================
# MOTION TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestMotions:
    """Tests for Motions v1 API."""

    async def test_create_motion(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test creating a motion."""
        response = await client.post(
            "/api/v1/governance/motions",
            json={
                "meeting_id": test_meeting.id,
                "title": "New Motion",
                "text": "Be it resolved that...",
                "reason": "Because it's needed",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Motion"
        assert data["workflow_state"] == "draft"

    async def test_list_motions(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting, test_motion: Motion):
        """Test listing motions."""
        response = await client.get(
            f"/api/v1/governance/motions?meeting_id={test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_get_motion(self, client: AsyncClient, auth_headers: dict, test_motion: Motion):
        """Test getting a motion."""
        response = await client.get(
            f"/api/v1/governance/motions/{test_motion.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_motion.id

    async def test_submit_motion(self, client: AsyncClient, auth_headers: dict, test_motion: Motion):
        """Test submitting a draft motion."""
        response = await client.post(
            f"/api/v1/governance/motions/{test_motion.id}/submit",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_state"] == "submitted"

    async def test_transition_motion(self, client: AsyncClient, auth_headers: dict, test_motion: Motion, db_session: AsyncSession):
        """Test transitioning motion workflow state."""
        # First submit the motion
        test_motion.workflow_state = MotionWorkflowState.SUBMITTED
        await db_session.flush()

        response = await client.post(
            f"/api/v1/governance/motions/{test_motion.id}/transition?new_state=discussion",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_state"] == "discussion"

    async def test_get_allowed_transitions(self, client: AsyncClient, auth_headers: dict, test_motion: Motion):
        """Test getting allowed transitions for a motion."""
        response = await client.get(
            f"/api/v1/governance/motions/{test_motion.id}/transitions",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_state"] == "draft"
        assert "submitted" in data["allowed_transitions"]


# ============================================================================
# POLL TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestPolls:
    """Tests for Polls v1 API."""

    async def test_create_poll(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting):
        """Test creating a poll."""
        response = await client.post(
            "/api/v1/governance/polls",
            json={
                "meeting_id": test_meeting.id,
                "title": "New Poll",
                "poll_type": "yes_no",
                "anonymous": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Poll"
        assert data["status"] == "draft"

    async def test_list_polls(self, client: AsyncClient, auth_headers: dict, test_meeting: Meeting, test_poll: Poll):
        """Test listing polls."""
        response = await client.get(
            f"/api/v1/governance/polls?meeting_id={test_meeting.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_get_poll(self, client: AsyncClient, auth_headers: dict, test_poll: Poll):
        """Test getting a poll."""
        response = await client.get(
            f"/api/v1/governance/polls/{test_poll.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_poll.id

    async def test_open_poll(self, client: AsyncClient, auth_headers: dict, test_poll: Poll):
        """Test opening a poll."""
        response = await client.post(
            f"/api/v1/governance/polls/{test_poll.id}/open",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"
        assert data["opened_at"] is not None

    async def test_close_poll(self, client: AsyncClient, auth_headers: dict, test_poll: Poll, db_session: AsyncSession):
        """Test closing a poll."""
        # First open the poll
        test_poll.status = PollStatus.OPEN
        test_poll.opened_at = datetime.now(timezone.utc)
        await db_session.flush()

        response = await client.post(
            f"/api/v1/governance/polls/{test_poll.id}/close",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"


# ============================================================================
# VOTE TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestVotes:
    """Tests for Votes v1 API."""

    async def test_cast_vote(self, client: AsyncClient, auth_headers: dict, test_poll: Poll, db_session: AsyncSession):
        """Test casting a vote."""
        # Open the poll first
        test_poll.status = PollStatus.OPEN
        test_poll.opened_at = datetime.now(timezone.utc)
        await db_session.flush()

        response = await client.post(
            "/api/v1/governance/votes",
            json={
                "poll_id": test_poll.id,
                "value": {"choice": "yes"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["value"] == {"choice": "yes"}

    async def test_list_votes(self, client: AsyncClient, auth_headers: dict, test_poll: Poll, test_user: User, db_session: AsyncSession):
        """Test listing votes."""
        # Open the poll and cast a vote
        test_poll.status = PollStatus.OPEN
        await db_session.flush()

        vote = Vote(
            poll_id=test_poll.id,
            user_id=test_user.id,
            value={"choice": "yes"},
            weight=1,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(vote)
        await db_session.flush()

        response = await client.get(
            f"/api/v1/governance/votes?poll_id={test_poll.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] >= 1

    async def test_cannot_vote_twice(self, client: AsyncClient, auth_headers: dict, test_poll: Poll, test_user: User, db_session: AsyncSession):
        """Test that users cannot vote twice on the same poll."""
        # Open the poll and cast a vote
        test_poll.status = PollStatus.OPEN
        await db_session.flush()

        vote = Vote(
            poll_id=test_poll.id,
            user_id=test_user.id,
            value={"choice": "yes"},
            weight=1,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(vote)
        await db_session.flush()

        # Try to vote again
        response = await client.post(
            "/api/v1/governance/votes",
            json={
                "poll_id": test_poll.id,
                "value": {"choice": "no"},
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "already voted" in response.json()["detail"].lower()


# ============================================================================
# ACCESS CONTROL TESTS
# ============================================================================

@pytest.mark.asyncio(loop_scope="function")
class TestAccessControl:
    """Tests for access control in governance endpoints."""

    async def test_unauthenticated_access_denied(self, client: AsyncClient, test_meeting: Meeting):
        """Test that unauthenticated requests are rejected."""
        response = await client.get(
            f"/api/v1/governance/meetings/{test_meeting.id}",
        )
        assert response.status_code == 401

    async def test_non_participant_denied_meeting_access(self, client: AsyncClient, test_meeting: Meeting, db_session: AsyncSession):
        """Test that non-participants cannot access meetings."""
        from app.core.security import get_password_hash, create_access_token
        from app.models.user import User

        # Create a different user
        other_user = User(
            email="other@example.com",
            name="Other User",
            password=get_password_hash("OtherPass123"),
            verified=True,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )
        db_session.add(other_user)
        await db_session.flush()

        other_token = create_access_token(data={"sub": other_user.id})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = await client.get(
            f"/api/v1/governance/meetings/{test_meeting.id}",
            headers=other_headers,
        )
        assert response.status_code == 403
