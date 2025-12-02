"""
Test configuration and fixtures for OrgSuite backend tests.
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
from app.models.journal_entry import JournalEntry, JournalEntryStatus
from app.models.journal_line import JournalLine
from app.models.donation import Donation, DonationStatus, PaymentMethod
from app.models.committee import Committee
from app.models.meeting import Meeting, MeetingStatus, MeetingType
from app.models.participant import Participant, ParticipantRole, AttendanceStatus
from app.models.agenda_item import AgendaItem, AgendaItemType, AgendaItemStatus
from app.models.motion import Motion, MotionWorkflowState
from app.models.poll import Poll, PollType, PollStatus
from app.models.vote import Vote


# Test database URL - uses in-memory SQLite for fast tests
# For more realistic tests, you could use a test PostgreSQL database
# Use a file-based SQLite DB to avoid :memory: multiple-connection issues
# with SQLAlchemy + aiosqlite (each new connection would see an empty DB).
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # Clean up test database file
    try:
        os.remove("./test.db")
    except OSError:
        pass


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        name="Test User",
        password_hash=get_password_hash("TestPass123"),
        verified=True,
        is_superadmin=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_user_token(test_user: User) -> str:
    """Create an access token for the test user."""
    return create_access_token(subject=test_user.id)


@pytest_asyncio.fixture
async def auth_headers(test_user_token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession, test_user: User) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Organization",
        description="A test organization for testing",
        owner_id=test_user.id,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(org)
    await db_session.flush()

    # Create owner membership
    membership = OrgMembership(
        organization_id=org.id,
        user_id=test_user.id,
        role=OrgMembershipRole.OWNER,
        is_active=True,
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(membership)
    await db_session.flush()

    return org


@pytest_asyncio.fixture
async def test_member(db_session: AsyncSession, test_org: Organization) -> Member:
    """Create a test member."""
    member = Member(
        organization_id=test_org.id,
        name="John Doe",
        email="john@example.com",
        status=MemberStatus.ACTIVE,
        member_type=MemberType.REGULAR,
        join_date=datetime.now(timezone.utc).date(),
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(member)
    await db_session.flush()
    return member


@pytest_asyncio.fixture
async def test_contact(db_session: AsyncSession, test_org: Organization) -> Contact:
    """Create a test contact."""
    contact = Contact(
        organization_id=test_org.id,
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        contact_type=ContactType.DONOR,
        is_active=True,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession, test_org: Organization) -> Account:
    """Create a test account."""
    account = Account(
        organization_id=test_org.id,
        code="1000",
        name="Cash",
        account_type=AccountType.ASSET,
        account_subtype=AccountSubtype.CASH_ON_HAND,
        is_active=True,
        is_system=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def test_revenue_account(db_session: AsyncSession, test_org: Organization) -> Account:
    """Create a test revenue account."""
    account = Account(
        organization_id=test_org.id,
        code="4000",
        name="Donations Revenue",
        account_type=AccountType.REVENUE,
        account_subtype=AccountSubType.OTHER_INCOME,
        is_active=True,
        is_system=False,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(account)
    await db_session.flush()
    return account


@pytest_asyncio.fixture
async def test_donation(
    db_session: AsyncSession, test_org: Organization, test_contact: Contact
) -> Donation:
    """Create a test donation."""
    donation = Donation(
        organization_id=test_org.id,
        donor_type="contact",
        donor_contact_id=test_contact.id,
        amount=100.00,
        status=DonationStatus.RECEIVED,
        payment_method=PaymentMethod.CHECK,
        donation_date=datetime.now(timezone.utc).date(),
        received_date=datetime.now(timezone.utc).date(),
        notes="Test donation",
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db_session.add(donation)
    await db_session.flush()
    return donation
