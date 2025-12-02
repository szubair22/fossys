"""
PostgreSQL-specific test configuration for OrgSuite backend.

This provides fixtures for running integration tests against a real PostgreSQL database.
Uses test containers for isolated, reproducible test environments.

Usage:
    pytest --postgres tests/

Environment variables:
    TEST_POSTGRES_URL: Override the default PostgreSQL test URL
"""
import asyncio
import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.db.base import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.organization import Organization
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.models.member import Member, MemberStatus, MemberType
from app.models.contact import Contact, ContactType
from app.models.account import Account, AccountType, AccountSubType
from app.models.committee import Committee
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.participant import Participant, ParticipantRole, AttendanceStatus


# PostgreSQL test database URL
# Can be overridden via environment variable
TEST_POSTGRES_URL = os.getenv(
    "TEST_POSTGRES_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/orgsuite_test"
)


def pytest_addoption(parser):
    """Add --postgres option to pytest command line."""
    parser.addoption(
        "--postgres",
        action="store_true",
        default=False,
        help="Run tests against PostgreSQL instead of SQLite"
    )


def pytest_configure(config):
    """Configure PostgreSQL markers."""
    config.addinivalue_line("markers", "postgres: mark test as requiring PostgreSQL")


def pytest_collection_modifyitems(config, items):
    """Skip PostgreSQL tests unless --postgres flag is used."""
    if config.getoption("--postgres"):
        return
    skip_postgres = pytest.mark.skip(reason="need --postgres option to run")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip_postgres)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def pg_engine():
    """Create a PostgreSQL test database engine."""
    engine = create_async_engine(
        TEST_POSTGRES_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(pg_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a PostgreSQL test database session."""
    async_session_maker = async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def pg_client(pg_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with PostgreSQL session override."""
    async def override_get_db():
        yield pg_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def pg_test_user(pg_session: AsyncSession) -> User:
    """Create a test user in PostgreSQL."""
    user = User(
        email="pg_testuser@example.com",
        name="PG Test User",
        password=get_password_hash("TestPass123"),
        verified=True,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(user)
    await pg_session.flush()
    return user


@pytest_asyncio.fixture
async def pg_test_user_token(pg_test_user: User) -> str:
    """Create an access token for the PostgreSQL test user."""
    return create_access_token(data={"sub": pg_test_user.id})


@pytest_asyncio.fixture
async def pg_auth_headers(pg_test_user_token: str) -> dict:
    """Create authorization headers for PostgreSQL tests."""
    return {"Authorization": f"Bearer {pg_test_user_token}"}


@pytest_asyncio.fixture
async def pg_test_org(pg_session: AsyncSession, pg_test_user: User) -> Organization:
    """Create a test organization in PostgreSQL."""
    org = Organization(
        name="PG Test Organization",
        description="A PostgreSQL test organization",
        owner_id=pg_test_user.id,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(org)
    await pg_session.flush()

    # Create owner membership
    membership = OrgMembership(
        organization_id=org.id,
        user_id=pg_test_user.id,
        role=OrgMembershipRole.OWNER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    pg_session.add(membership)
    await pg_session.flush()

    return org


@pytest_asyncio.fixture
async def pg_test_member(pg_session: AsyncSession, pg_test_org: Organization) -> Member:
    """Create a test member in PostgreSQL."""
    member = Member(
        organization_id=pg_test_org.id,
        name="PG John Doe",
        email="pg_john@example.com",
        status=MemberStatus.ACTIVE,
        member_type=MemberType.REGULAR,
        join_date=datetime.now(timezone.utc).date(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(member)
    await pg_session.flush()
    return member


@pytest_asyncio.fixture
async def pg_test_contact(pg_session: AsyncSession, pg_test_org: Organization) -> Contact:
    """Create a test contact in PostgreSQL."""
    contact = Contact(
        organization_id=pg_test_org.id,
        first_name="PG Jane",
        last_name="Smith",
        email="pg_jane@example.com",
        contact_type=ContactType.DONOR,
        is_active=True,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(contact)
    await pg_session.flush()
    return contact


@pytest_asyncio.fixture
async def pg_test_account(pg_session: AsyncSession, pg_test_org: Organization) -> Account:
    """Create a test account in PostgreSQL."""
    account = Account(
        organization_id=pg_test_org.id,
        code="1000",
        name="PG Cash",
        account_type=AccountType.ASSET,
        account_subtype=AccountSubtype.CASH_ON_HAND,
        is_active=True,
        is_system=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(account)
    await pg_session.flush()
    return account


@pytest_asyncio.fixture
async def pg_test_committee(pg_session: AsyncSession, pg_test_org: Organization, pg_test_user: User) -> Committee:
    """Create a test committee in PostgreSQL."""
    committee = Committee(
        organization_id=pg_test_org.id,
        name="PG Test Committee",
        description="A PostgreSQL test committee",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    committee.admins = [pg_test_user]
    pg_session.add(committee)
    await pg_session.flush()
    return committee


@pytest_asyncio.fixture
async def pg_test_meeting(pg_session: AsyncSession, pg_test_committee: Committee, pg_test_user: User) -> Meeting:
    """Create a test meeting in PostgreSQL."""
    from datetime import timedelta
    meeting = Meeting(
        title="PG Test Meeting",
        description="A PostgreSQL test meeting",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        status=MeetingStatus.SCHEDULED,
        meeting_type=MeetingType.GENERAL,
        committee_id=pg_test_committee.id,
        created_by_id=pg_test_user.id,
        jitsi_room="pg-test-room-123",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(meeting)
    await pg_session.flush()

    # Add creator as participant
    participant = Participant(
        meeting_id=meeting.id,
        user_id=pg_test_user.id,
        role=ParticipantRole.ADMIN,
        is_present=False,
        attendance_status=AttendanceStatus.INVITED,
        can_vote=True,
        vote_weight=1,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    pg_session.add(participant)
    await pg_session.flush()

    return meeting
