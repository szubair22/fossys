"""
Poll and vote endpoints - compatible with PocketBase SDK.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.meeting import Meeting
from app.core.permissions import require_min_role, OrgMembershipRole, resolve_meeting_org_id
from app.models.poll import Poll, PollType, PollStatus
from app.models.vote import Vote
from app.schemas.poll import PollCreate, PollUpdate, PollResponse, VoteCreate, VoteResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def poll_to_response(poll: Poll, expand: Optional[dict] = None) -> PollResponse:
    """Convert Poll model to PollResponse schema."""
    return PollResponse(
        id=poll.id,
        meeting=poll.meeting_id,
        motion=poll.motion_id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type.value if isinstance(poll.poll_type, PollType) else poll.poll_type,
        options=poll.options,
        status=poll.status.value if isinstance(poll.status, PollStatus) else poll.status,
        results=poll.results,
        anonymous=poll.anonymous,
        opened_at=poll.opened_at,
        closed_at=poll.closed_at,
        created_by=poll.created_by_id,
        poll_category=poll.poll_category,
        winning_option=poll.winning_option,
        created=poll.created,
        updated=poll.updated,
        expand=expand,
    )


def vote_to_response(vote: Vote) -> VoteResponse:
    """Convert Vote model to VoteResponse schema."""
    return VoteResponse(
        id=vote.id,
        poll=vote.poll_id,
        user=vote.user_id,
        value=vote.value,
        weight=vote.weight,
        delegated_from=vote.delegated_from_id,
        created=vote.created,
        updated=vote.updated,
    )


@router.get("/records", response_model=PaginatedResponse[PollResponse])
async def list_polls(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List polls.
    PocketBase SDK: pb.collection('polls').getList()
    """
    query = select(Poll)

    # Parse simple filters if provided
    if filter:
        if "meeting=" in filter:
            meeting_id = filter.split("meeting=")[1].split("'")[1] if "'" in filter else filter.split("meeting=")[1].split()[0]
            query = query.where(Poll.meeting_id == meeting_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply sorting
    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(Poll, field_name):
                query = query.order_by(getattr(Poll, field_name).desc())
        else:
            if hasattr(Poll, sort):
                query = query.order_by(getattr(Poll, sort).asc())
    else:
        query = query.order_by(Poll.created.desc())

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    polls = result.scalars().all()

    # Build response
    items = [poll_to_response(p) for p in polls]

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=PollResponse, status_code=status.HTTP_200_OK)
async def create_poll(
    poll_data: PollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create poll.
    PocketBase SDK: pb.collection('polls').create()
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == poll_data.meeting)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Organization membership enforcement: require MEMBER for create
    org_id = await resolve_meeting_org_id(db, meeting) if meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Parse poll type
    try:
        poll_type_enum = PollType(poll_data.poll_type)
    except ValueError:
        poll_type_enum = PollType.YES_NO

    # Create poll
    poll = Poll(
        meeting_id=poll_data.meeting,
        motion_id=poll_data.motion,
        title=poll_data.title,
        description=poll_data.description,
        poll_type=poll_type_enum,
        options=poll_data.options,
        anonymous=poll_data.anonymous,
        status=PollStatus.DRAFT,
        created_by_id=current_user.id,
    )

    db.add(poll)
    await db.flush()

    return poll_to_response(poll)


@router.get("/records/{poll_id}", response_model=PollResponse)
async def get_poll(
    poll_id: str,
    expand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get poll by ID.
    PocketBase SDK: pb.collection('polls').getOne()
    """
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    return poll_to_response(poll)


@router.patch("/records/{poll_id}", response_model=PollResponse)
async def update_poll(
    poll_id: str,
    poll_data: PollUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update poll.
    PocketBase SDK: pb.collection('polls').update()
    """
    result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    # Role enforcement: require MEMBER for updates if org context
    poll_meeting_result = await db.execute(select(Meeting).where(Meeting.id == poll.meeting_id))
    parent_meeting = poll_meeting_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Update fields
    if poll_data.title is not None:
        poll.title = poll_data.title
    if poll_data.description is not None:
        poll.description = poll_data.description
    if poll_data.status is not None:
        try:
            new_status = PollStatus(poll_data.status)
            # Handle status transitions
            if new_status == PollStatus.OPEN and poll.opened_at is None:
                poll.opened_at = datetime.now(timezone.utc)
            elif new_status == PollStatus.CLOSED and poll.closed_at is None:
                poll.closed_at = datetime.now(timezone.utc)
            poll.status = new_status
        except ValueError:
            pass
    if poll_data.results is not None:
        poll.results = poll_data.results
    if poll_data.poll_category is not None:
        poll.poll_category = poll_data.poll_category
    if poll_data.winning_option is not None:
        poll.winning_option = poll_data.winning_option

    poll.updated = datetime.now(timezone.utc)
    await db.flush()

    return poll_to_response(poll)


@router.delete("/records/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete poll.
    PocketBase SDK: pb.collection('polls').delete()
    """
    result = await db.execute(select(Poll).where(Poll.id == poll_id))
    poll = result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    # Require ADMIN for delete if org context
    poll_meeting_result = await db.execute(select(Meeting).where(Meeting.id == poll.meeting_id))
    parent_meeting = poll_meeting_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.ADMIN)

    await db.delete(poll)
    await db.flush()

    return None


# Votes router
votes_router = APIRouter()


@votes_router.get("/records", response_model=PaginatedResponse[VoteResponse])
async def list_votes(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    List votes.
    PocketBase SDK: pb.collection('votes').getList()
    """
    query = select(Vote)

    # Parse simple filters if provided
    if filter:
        if "poll=" in filter:
            poll_id = filter.split("poll=")[1].split("'")[1] if "'" in filter else filter.split("poll=")[1].split()[0]
            query = query.where(Vote.poll_id == poll_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    votes = result.scalars().all()

    # Build response
    items = [vote_to_response(v) for v in votes]

    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@votes_router.post("/records", response_model=VoteResponse, status_code=status.HTTP_200_OK)
async def cast_vote(
    vote_data: VoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cast a vote.
    PocketBase SDK: pb.collection('votes').create()
    """
    # Check poll exists and is open
    poll_result = await db.execute(
        select(Poll).where(Poll.id == vote_data.poll)
    )
    poll = poll_result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    if poll.status != PollStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Poll is not open for voting"
        )

    # Check if user already voted
    existing_result = await db.execute(
        select(Vote).where(
            Vote.poll_id == vote_data.poll,
            Vote.user_id == current_user.id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already voted on this poll"
        )

    # Organization membership enforcement: require MEMBER for voting
    poll_meeting_result = await db.execute(select(Meeting).where(Meeting.id == poll.meeting_id))
    parent_meeting = poll_meeting_result.scalar_one_or_none()
    org_id = await resolve_meeting_org_id(db, parent_meeting) if parent_meeting else None
    if org_id:
        await require_min_role(db, current_user.id, org_id, OrgMembershipRole.MEMBER)

    # Create vote
    vote = Vote(
        poll_id=vote_data.poll,
        user_id=current_user.id,
        value=vote_data.value,
        weight=1,
    )

    db.add(vote)
    await db.flush()

    return vote_to_response(vote)
