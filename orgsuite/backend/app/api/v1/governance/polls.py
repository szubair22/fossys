"""
Poll and Vote endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/polls/* and /api/v1/governance/votes/*
endpoints that follow the same patterns as the membership and finance modules.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.participant import Participant, ParticipantRole
from app.models.poll import Poll, PollType, PollStatus
from app.models.vote import Vote
from app.schemas.governance_v1 import (
    PollV1Create, PollV1Update, PollV1Response, PollV1ListResponse,
    VoteV1Create, VoteV1Response, VoteV1ListResponse
)

router = APIRouter()
votes_router = APIRouter()


def poll_to_response(poll: Poll) -> PollV1Response:
    """Convert Poll model to PollV1Response schema."""
    return PollV1Response(
        id=poll.id,
        meeting_id=poll.meeting_id,
        motion_id=poll.motion_id,
        title=poll.title,
        description=poll.description,
        poll_type=poll.poll_type.value if isinstance(poll.poll_type, PollType) else poll.poll_type,
        options=poll.options,
        status=poll.status.value if isinstance(poll.status, PollStatus) else poll.status,
        results=poll.results,
        anonymous=poll.anonymous,
        opened_at=poll.opened_at,
        closed_at=poll.closed_at,
        created_by_id=poll.created_by_id,
        poll_category=poll.poll_category,
        winning_option=poll.winning_option,
        created=poll.created,
        updated=poll.updated,
    )


def vote_to_response(vote: Vote) -> VoteV1Response:
    """Convert Vote model to VoteV1Response schema."""
    return VoteV1Response(
        id=vote.id,
        poll_id=vote.poll_id,
        user_id=vote.user_id,
        value=vote.value,
        weight=vote.weight,
        delegated_from_id=vote.delegated_from_id,
        created=vote.created,
        updated=vote.updated,
    )


async def check_meeting_access(
    meeting_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the meeting."""
    # Get meeting
    result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()

    if meeting is None:
        return False

    # Creator has full access
    if meeting.created_by_id == user.id:
        return True

    # Check if user is participant
    participant_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == meeting_id,
            Participant.user_id == user.id
        )
    )
    participant = participant_result.scalar_one_or_none()

    if participant is None:
        return False

    if require_admin:
        return participant.role in [ParticipantRole.ADMIN, ParticipantRole.MODERATOR]

    return True


def calculate_poll_results(votes: list[Vote]) -> dict:
    """Calculate poll results from votes."""
    results = {
        "total_votes": len(votes),
        "breakdown": {}
    }

    for vote in votes:
        choice = vote.value.get("choice") if isinstance(vote.value, dict) else vote.value
        if choice:
            weight = vote.weight or 1
            if choice in results["breakdown"]:
                results["breakdown"][choice] += weight
            else:
                results["breakdown"][choice] = weight

    return results


# ============================================================================
# Poll Endpoints
# ============================================================================

@router.get("", response_model=PollV1ListResponse)
async def list_polls(
    meeting_id: str = Query(..., description="Meeting ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List polls for a meeting.
    Requires meeting access.
    """
    # Check access
    if not await check_meeting_access(meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )

    query = select(Poll).where(Poll.meeting_id == meeting_id)

    # Apply status filter
    if status_filter:
        try:
            status_enum = PollStatus(status_filter)
            query = query.where(Poll.status == status_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Poll.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    polls = result.scalars().all()

    items = [poll_to_response(p) for p in polls]

    return PollV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=PollV1Response, status_code=status.HTTP_201_CREATED)
async def create_poll(
    poll_data: PollV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a poll.
    Requires meeting admin access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == poll_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check admin access
    if not await check_meeting_access(poll_data.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create polls in this meeting"
        )

    # Parse poll type
    try:
        poll_type_enum = PollType(poll_data.poll_type)
    except ValueError:
        poll_type_enum = PollType.YES_NO

    # Create poll
    poll = Poll(
        meeting_id=poll_data.meeting_id,
        motion_id=poll_data.motion_id,
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


@router.get("/{poll_id}", response_model=PollV1Response)
async def get_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get poll by ID.
    Requires meeting access.
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

    # Check access
    if not await check_meeting_access(poll.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this poll"
        )

    return poll_to_response(poll)


@router.patch("/{poll_id}", response_model=PollV1Response)
async def update_poll(
    poll_id: str,
    poll_data: PollV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update poll.
    Requires meeting admin access.
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

    # Check admin access
    if not await check_meeting_access(poll.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this poll"
        )

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


@router.delete("/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete poll.
    Only draft polls can be deleted. Requires meeting admin access.
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

    # Check admin access
    if not await check_meeting_access(poll.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this poll"
        )

    # Only draft polls can be deleted
    if poll.status != PollStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft polls can be deleted"
        )

    await db.delete(poll)
    await db.flush()

    return None


@router.post("/{poll_id}/open", response_model=PollV1Response)
async def open_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Open a poll for voting.
    Requires meeting admin access.
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

    # Check admin access
    if not await check_meeting_access(poll.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to open this poll"
        )

    if poll.status != PollStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft polls can be opened"
        )

    poll.status = PollStatus.OPEN
    poll.opened_at = datetime.now(timezone.utc)
    poll.updated = datetime.now(timezone.utc)
    await db.flush()

    return poll_to_response(poll)


@router.post("/{poll_id}/close", response_model=PollV1Response)
async def close_poll(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close a poll and calculate results.
    Requires meeting admin access.
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

    # Check admin access
    if not await check_meeting_access(poll.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to close this poll"
        )

    if poll.status != PollStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open polls can be closed"
        )

    # Get votes and calculate results
    votes_result = await db.execute(
        select(Vote).where(Vote.poll_id == poll_id)
    )
    votes = votes_result.scalars().all()

    results = calculate_poll_results(list(votes))

    poll.status = PollStatus.CLOSED
    poll.closed_at = datetime.now(timezone.utc)
    poll.results = results
    poll.updated = datetime.now(timezone.utc)
    await db.flush()

    return poll_to_response(poll)


@router.get("/{poll_id}/results")
async def get_poll_results(
    poll_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get poll results.
    For open polls, calculates live results. For closed polls, returns stored results.
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

    # Check access
    if not await check_meeting_access(poll.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this poll"
        )

    # Return stored results if available
    if poll.results:
        return poll.results

    # Calculate live results
    votes_result = await db.execute(
        select(Vote).where(Vote.poll_id == poll_id)
    )
    votes = votes_result.scalars().all()

    return calculate_poll_results(list(votes))


# ============================================================================
# Vote Endpoints
# ============================================================================

@votes_router.get("", response_model=VoteV1ListResponse)
async def list_votes(
    poll_id: str = Query(..., description="Poll ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List votes for a poll.
    Requires meeting access. For anonymous polls, only returns vote values.
    """
    # Get poll to check meeting access
    poll_result = await db.execute(
        select(Poll).where(Poll.id == poll_id)
    )
    poll = poll_result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    # Check access
    if not await check_meeting_access(poll.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this poll"
        )

    query = select(Vote).where(Vote.poll_id == poll_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    votes = result.scalars().all()

    # For anonymous polls, hide user IDs (except own vote)
    items = []
    for v in votes:
        response = vote_to_response(v)
        if poll.anonymous and v.user_id != current_user.id:
            response.user_id = "anonymous"
            response.delegated_from_id = None
        items.append(response)

    return VoteV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@votes_router.post("", response_model=VoteV1Response, status_code=status.HTTP_201_CREATED)
async def cast_vote(
    vote_data: VoteV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cast a vote.
    Requires being a participant with voting rights.
    """
    # Check poll exists and is open
    poll_result = await db.execute(
        select(Poll).where(Poll.id == vote_data.poll_id)
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

    # Check user is participant with voting rights
    participant_result = await db.execute(
        select(Participant).where(
            Participant.meeting_id == poll.meeting_id,
            Participant.user_id == current_user.id,
            Participant.can_vote == True
        )
    )
    participant = participant_result.scalar_one_or_none()

    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to vote in this poll"
        )

    # Check if user already voted
    existing_result = await db.execute(
        select(Vote).where(
            Vote.poll_id == vote_data.poll_id,
            Vote.user_id == current_user.id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already voted on this poll"
        )

    # Create vote
    vote = Vote(
        poll_id=vote_data.poll_id,
        user_id=current_user.id,
        value=vote_data.value,
        weight=participant.vote_weight or 1,
    )

    db.add(vote)
    await db.flush()

    return vote_to_response(vote)


@votes_router.get("/{vote_id}", response_model=VoteV1Response)
async def get_vote(
    vote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get vote by ID.
    Users can only see their own votes or all votes if not anonymous.
    """
    result = await db.execute(
        select(Vote).where(Vote.id == vote_id)
    )
    vote = result.scalar_one_or_none()

    if vote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vote not found"
        )

    # Get poll to check access and anonymity
    poll_result = await db.execute(
        select(Poll).where(Poll.id == vote.poll_id)
    )
    poll = poll_result.scalar_one_or_none()

    if poll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )

    # Check access
    if not await check_meeting_access(poll.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vote"
        )

    # For anonymous polls, only allow viewing own vote
    if poll.anonymous and vote.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' votes in anonymous polls"
        )

    return vote_to_response(vote)


@votes_router.delete("/{vote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vote(
    vote_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete/retract a vote.
    Only allowed while poll is open and only for own votes.
    """
    result = await db.execute(
        select(Vote).where(Vote.id == vote_id)
    )
    vote = result.scalar_one_or_none()

    if vote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vote not found"
        )

    # Only owner can delete their vote
    if vote.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own votes"
        )

    # Check poll is still open
    poll_result = await db.execute(
        select(Poll).where(Poll.id == vote.poll_id)
    )
    poll = poll_result.scalar_one_or_none()

    if poll is None or poll.status != PollStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retract votes while poll is open"
        )

    await db.delete(vote)
    await db.flush()

    return None
