"""
Motion endpoints for OrgSuite Governance module - v1 API.

This provides the new /api/v1/governance/motions/* endpoints that follow
the same patterns as the membership and finance modules.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.participant import Participant, ParticipantRole
from app.models.motion import Motion, MotionWorkflowState
from app.schemas.governance_v1 import (
    MotionV1Create, MotionV1Update, MotionV1Response,
    MotionV1ListResponse
)

router = APIRouter()

# Motion workflow state transitions
MOTION_TRANSITIONS = {
    'draft': ['submitted', 'withdrawn'],
    'submitted': ['screening', 'discussion', 'withdrawn'],
    'screening': ['discussion', 'rejected', 'withdrawn'],
    'discussion': ['voting', 'referred', 'withdrawn'],
    'voting': ['accepted', 'rejected'],
    'accepted': [],
    'rejected': [],
    'withdrawn': [],
    'referred': ['discussion']
}


def motion_to_response(motion: Motion) -> MotionV1Response:
    """Convert Motion model to MotionV1Response schema."""
    response = MotionV1Response(
        id=motion.id,
        meeting_id=motion.meeting_id,
        agenda_item_id=motion.agenda_item_id,
        number=motion.number,
        title=motion.title,
        text=motion.text,
        reason=motion.reason,
        submitter_id=motion.submitter_id,
        supporter_ids=[s.id for s in motion.supporters] if motion.supporters else [],
        workflow_state=motion.workflow_state.value if isinstance(motion.workflow_state, MotionWorkflowState) else motion.workflow_state,
        category=motion.category,
        vote_result=motion.vote_result,
        final_notes=motion.final_notes,
        attachments=motion.attachments,
        created=motion.created,
        updated=motion.updated,
    )

    # Add expanded submitter info if available
    if motion.submitter:
        response.submitter_name = motion.submitter.name or motion.submitter.display_name

    return response


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


@router.get("", response_model=MotionV1ListResponse)
async def list_motions(
    meeting_id: str = Query(..., description="Meeting ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    workflow_state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List motions for a meeting.
    Requires meeting access.
    """
    # Check access
    if not await check_meeting_access(meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )

    query = select(Motion).options(
        selectinload(Motion.supporters),
        selectinload(Motion.submitter)
    ).where(Motion.meeting_id == meeting_id)

    # Apply workflow state filter
    if workflow_state:
        try:
            state_enum = MotionWorkflowState(workflow_state)
            query = query.where(Motion.workflow_state == state_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(Motion.created.desc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    motions = result.unique().scalars().all()

    items = [motion_to_response(m) for m in motions]

    return MotionV1ListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=MotionV1Response, status_code=status.HTTP_201_CREATED)
async def create_motion(
    motion_data: MotionV1Create,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a motion.
    Requires meeting access.
    """
    # Check meeting exists
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == motion_data.meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()

    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Check access
    if not await check_meeting_access(motion_data.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add motions to this meeting"
        )

    # Generate motion number if not provided
    number = motion_data.number
    if not number:
        count_result = await db.execute(
            select(func.count()).where(Motion.meeting_id == motion_data.meeting_id)
        )
        count = count_result.scalar() or 0
        number = f"M-{count + 1:03d}"

    # Create motion
    motion = Motion(
        meeting_id=motion_data.meeting_id,
        agenda_item_id=motion_data.agenda_item_id,
        number=number,
        title=motion_data.title,
        text=motion_data.text,
        reason=motion_data.reason,
        category=motion_data.category,
        submitter_id=current_user.id,
        workflow_state=MotionWorkflowState.DRAFT,
    )

    db.add(motion)
    await db.flush()

    # Reload with supporters and submitter
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters), selectinload(Motion.submitter))
        .where(Motion.id == motion.id)
    )
    motion = result.scalar_one()

    return motion_to_response(motion)


@router.get("/{motion_id}", response_model=MotionV1Response)
async def get_motion(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get motion by ID.
    Requires meeting access.
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters), selectinload(Motion.submitter))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check access
    if not await check_meeting_access(motion.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this motion"
        )

    return motion_to_response(motion)


@router.patch("/{motion_id}", response_model=MotionV1Response)
async def update_motion(
    motion_id: str,
    motion_data: MotionV1Update,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update motion.
    Submitter can update draft motions. Admins can update any motion.
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters), selectinload(Motion.submitter))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check permission
    is_submitter = motion.submitter_id == current_user.id
    is_admin = await check_meeting_access(motion.meeting_id, current_user, db, require_admin=True)

    if not is_submitter and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this motion"
        )

    # Submitter can only update draft motions
    if is_submitter and not is_admin:
        if motion.workflow_state != MotionWorkflowState.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only edit draft motions"
            )

    # Update fields
    if motion_data.title is not None:
        motion.title = motion_data.title
    if motion_data.text is not None:
        motion.text = motion_data.text
    if motion_data.reason is not None:
        motion.reason = motion_data.reason
    if motion_data.category is not None:
        motion.category = motion_data.category
    if motion_data.workflow_state is not None:
        # Validate state transition
        current_state = motion.workflow_state.value if isinstance(motion.workflow_state, MotionWorkflowState) else motion.workflow_state
        allowed_transitions = MOTION_TRANSITIONS.get(current_state, [])
        if motion_data.workflow_state not in allowed_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from {current_state} to {motion_data.workflow_state}"
            )
        try:
            motion.workflow_state = MotionWorkflowState(motion_data.workflow_state)
        except ValueError:
            pass
    if motion_data.vote_result is not None:
        motion.vote_result = motion_data.vote_result
    if motion_data.final_notes is not None:
        motion.final_notes = motion_data.final_notes

    motion.updated = datetime.now(timezone.utc)
    await db.flush()

    return motion_to_response(motion)


@router.delete("/{motion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_motion(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete motion.
    Only draft motions can be deleted. Requires being submitter or admin.
    """
    result = await db.execute(
        select(Motion).where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check permission
    is_submitter = motion.submitter_id == current_user.id
    is_admin = await check_meeting_access(motion.meeting_id, current_user, db, require_admin=True)

    if not is_submitter and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this motion"
        )

    # Only draft motions can be deleted
    if motion.workflow_state != MotionWorkflowState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft motions can be deleted"
        )

    await db.delete(motion)
    await db.flush()

    return None


@router.post("/{motion_id}/submit", response_model=MotionV1Response)
async def submit_motion(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit a draft motion for consideration.
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters), selectinload(Motion.submitter))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check permission - submitter or admin
    is_submitter = motion.submitter_id == current_user.id
    is_admin = await check_meeting_access(motion.meeting_id, current_user, db, require_admin=True)

    if not is_submitter and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit this motion"
        )

    if motion.workflow_state != MotionWorkflowState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft motions can be submitted"
        )

    motion.workflow_state = MotionWorkflowState.SUBMITTED
    motion.updated = datetime.now(timezone.utc)
    await db.flush()

    return motion_to_response(motion)


@router.post("/{motion_id}/transition", response_model=MotionV1Response)
async def transition_motion(
    motion_id: str,
    new_state: str = Query(..., description="New workflow state"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition motion to a new workflow state.
    Requires meeting admin access.
    """
    result = await db.execute(
        select(Motion)
        .options(selectinload(Motion.supporters), selectinload(Motion.submitter))
        .where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check admin access
    if not await check_meeting_access(motion.meeting_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to transition this motion"
        )

    # Validate state transition
    current_state = motion.workflow_state.value if isinstance(motion.workflow_state, MotionWorkflowState) else motion.workflow_state
    allowed_transitions = MOTION_TRANSITIONS.get(current_state, [])

    if new_state not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_state} to {new_state}. Allowed: {allowed_transitions}"
        )

    try:
        motion.workflow_state = MotionWorkflowState(new_state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow state: {new_state}"
        )

    motion.updated = datetime.now(timezone.utc)
    await db.flush()

    return motion_to_response(motion)


@router.get("/{motion_id}/transitions")
async def get_allowed_transitions(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get allowed workflow transitions for a motion.
    """
    result = await db.execute(
        select(Motion).where(Motion.id == motion_id)
    )
    motion = result.scalar_one_or_none()

    if motion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Motion not found"
        )

    # Check access
    if not await check_meeting_access(motion.meeting_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this motion"
        )

    current_state = motion.workflow_state.value if isinstance(motion.workflow_state, MotionWorkflowState) else motion.workflow_state
    allowed = MOTION_TRANSITIONS.get(current_state, [])

    return {
        "current_state": current_state,
        "allowed_transitions": allowed
    }
