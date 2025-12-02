"""
Opportunity endpoints for CRM module.

Permissions:
- List/Get: requires 'viewer' role in organization
- Create: requires 'member' role in organization
- Update: requires 'member' role (own) or 'admin' (any)
- Delete: requires 'admin' role in organization
- Stage change: requires 'member' role (own) or 'admin' (any)
"""
from datetime import datetime, timezone, date
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_min_role, is_admin_or_owner
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityStage, OpportunitySource, VALID_STAGE_TRANSITIONS
from app.models.contact import Contact
from app.models.project import Project
from app.models.org_membership import OrgMembershipRole
from app.schemas.crm import (
    OpportunityCreate, OpportunityUpdate, OpportunityStageChange,
    OpportunityResponse, OpportunityListResponse
)
from app.services.settings import get_finance_config

router = APIRouter()


async def opportunity_to_response(opportunity: Opportunity, db: AsyncSession) -> OpportunityResponse:
    """Convert Opportunity model to response schema with expanded fields."""
    contact_name = None
    project_name = None
    owner_name = None

    if opportunity.related_contact_id:
        result = await db.execute(
            select(Contact.name).where(Contact.id == opportunity.related_contact_id)
        )
        contact_name = result.scalar_one_or_none()

    if opportunity.related_project_id:
        result = await db.execute(
            select(Project.name).where(Project.id == opportunity.related_project_id)
        )
        project_name = result.scalar_one_or_none()

    if opportunity.owner_user_id:
        result = await db.execute(
            select(User.name).where(User.id == opportunity.owner_user_id)
        )
        owner_name = result.scalar_one_or_none()

    return OpportunityResponse(
        id=opportunity.id,
        organization_id=opportunity.organization_id,
        title=opportunity.title,
        description=opportunity.description,
        related_contact_id=opportunity.related_contact_id,
        related_project_id=opportunity.related_project_id,
        amount=opportunity.amount,
        currency=opportunity.currency,
        stage=opportunity.stage.value if isinstance(opportunity.stage, OpportunityStage) else opportunity.stage,
        probability=opportunity.probability,
        expected_close_date=opportunity.expected_close_date,
        actual_close_date=opportunity.actual_close_date,
        source=opportunity.source.value if isinstance(opportunity.source, OpportunitySource) else opportunity.source,
        owner_user_id=opportunity.owner_user_id,
        created=opportunity.created,
        updated=opportunity.updated,
        related_contact_name=contact_name,
        related_project_name=project_name,
        owner_name=owner_name,
    )


@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    organization_id: str = Query(..., description="Organization ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=100),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    owner_user_id: Optional[str] = Query(None, description="Filter by owner"),
    related_contact_id: Optional[str] = Query(None, description="Filter by contact"),
    related_project_id: Optional[str] = Query(None, description="Filter by project"),
    search: Optional[str] = Query(None, description="Search title/description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List opportunities for an organization."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    query = select(Opportunity).where(Opportunity.organization_id == organization_id)

    # Apply filters
    if stage:
        try:
            stage_enum = OpportunityStage(stage)
            query = query.where(Opportunity.stage == stage_enum)
        except ValueError:
            pass

    if owner_user_id:
        query = query.where(Opportunity.owner_user_id == owner_user_id)

    if related_contact_id:
        query = query.where(Opportunity.related_contact_id == related_contact_id)

    if related_project_id:
        query = query.where(Opportunity.related_project_id == related_project_id)

    if search:
        search_filter = (
            Opportunity.title.ilike(f"%{search}%") |
            Opportunity.description.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    # Order by created desc
    query = query.order_by(Opportunity.created.desc())

    # Pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    opportunities = result.scalars().all()

    items = [await opportunity_to_response(o, db) for o in opportunities]
    return OpportunityListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/opportunities", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opp_data: OpportunityCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new opportunity."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    # Validate enums
    try:
        stage_enum = OpportunityStage(opp_data.stage)
    except ValueError:
        stage_enum = OpportunityStage.PROSPECTING

    try:
        source_enum = OpportunitySource(opp_data.source)
    except ValueError:
        source_enum = OpportunitySource.OTHER

    # Get default currency from finance config
    finance_config = await get_finance_config(db, organization_id)
    currency = opp_data.currency or (finance_config.default_currency if finance_config else "USD")

    opportunity = Opportunity(
        organization_id=organization_id,
        title=opp_data.title,
        description=opp_data.description,
        related_contact_id=opp_data.related_contact_id,
        related_project_id=opp_data.related_project_id,
        amount=opp_data.amount,
        currency=currency,
        stage=stage_enum,
        probability=opp_data.probability,
        expected_close_date=opp_data.expected_close_date,
        source=source_enum,
        owner_user_id=current_user.id,  # Assign to creator by default
    )

    db.add(opportunity)
    await db.flush()
    await db.refresh(opportunity)

    return await opportunity_to_response(opportunity, db)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an opportunity by ID."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.organization_id == organization_id
        )
    )
    opportunity = result.scalar_one_or_none()

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    return await opportunity_to_response(opportunity, db)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: str,
    opp_data: OpportunityUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an opportunity."""
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.organization_id == organization_id
        )
    )
    opportunity = result.scalar_one_or_none()

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Members can only update their own opportunities unless admin
    if not is_admin_or_owner(membership) and opportunity.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own opportunities"
        )

    # Update fields
    if opp_data.title is not None:
        opportunity.title = opp_data.title
    if opp_data.description is not None:
        opportunity.description = opp_data.description
    if opp_data.related_contact_id is not None:
        opportunity.related_contact_id = opp_data.related_contact_id or None
    if opp_data.related_project_id is not None:
        opportunity.related_project_id = opp_data.related_project_id or None
    if opp_data.amount is not None:
        opportunity.amount = opp_data.amount
    if opp_data.currency is not None:
        opportunity.currency = opp_data.currency
    if opp_data.probability is not None:
        opportunity.probability = opp_data.probability
    if opp_data.expected_close_date is not None:
        opportunity.expected_close_date = opp_data.expected_close_date
    if opp_data.actual_close_date is not None:
        opportunity.actual_close_date = opp_data.actual_close_date
    if opp_data.source is not None:
        try:
            opportunity.source = OpportunitySource(opp_data.source)
        except ValueError:
            pass
    if opp_data.owner_user_id is not None and is_admin_or_owner(membership):
        opportunity.owner_user_id = opp_data.owner_user_id

    opportunity.updated = datetime.now(timezone.utc)
    await db.flush()

    return await opportunity_to_response(opportunity, db)


@router.delete("/opportunities/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an opportunity. Requires admin role."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.ADMIN)

    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.organization_id == organization_id
        )
    )
    opportunity = result.scalar_one_or_none()

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    await db.delete(opportunity)
    await db.flush()

    return None


@router.post("/opportunities/{opportunity_id}/stage", response_model=OpportunityResponse)
async def change_opportunity_stage(
    opportunity_id: str,
    stage_change: OpportunityStageChange,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change the stage of an opportunity.

    Enforces valid stage transitions:
    - prospecting -> qualification, lost
    - qualification -> prospecting, proposal_made, lost
    - proposal_made -> qualification, negotiation, won, lost
    - negotiation -> proposal_made, won, lost
    - won -> (terminal)
    - lost -> prospecting (can reopen)
    """
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.organization_id == organization_id
        )
    )
    opportunity = result.scalar_one_or_none()

    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found"
        )

    # Members can only update their own opportunities unless admin
    if not is_admin_or_owner(membership) and opportunity.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change stage on your own opportunities"
        )

    # Validate new stage
    try:
        new_stage = OpportunityStage(stage_change.new_stage)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage: {stage_change.new_stage}"
        )

    # Check if transition is valid
    if not opportunity.can_transition_to(new_stage):
        allowed = [s.value for s in VALID_STAGE_TRANSITIONS.get(opportunity.stage, [])]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{opportunity.stage.value}' to '{new_stage.value}'. Allowed: {allowed}"
        )

    # Update stage
    opportunity.stage = new_stage

    # Set actual_close_date when won or lost
    if new_stage in (OpportunityStage.WON, OpportunityStage.LOST):
        opportunity.actual_close_date = date.today()
    elif new_stage == OpportunityStage.PROSPECTING:
        # Reopening: clear close date
        opportunity.actual_close_date = None

    # Update probability based on stage
    stage_probabilities = {
        OpportunityStage.PROSPECTING: 10,
        OpportunityStage.QUALIFICATION: 25,
        OpportunityStage.PROPOSAL_MADE: 50,
        OpportunityStage.NEGOTIATION: 75,
        OpportunityStage.WON: 100,
        OpportunityStage.LOST: 0,
    }
    opportunity.probability = stage_probabilities.get(new_stage, opportunity.probability)

    opportunity.updated = datetime.now(timezone.utc)
    await db.flush()

    return await opportunity_to_response(opportunity, db)
