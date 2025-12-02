"""
Lead endpoints for CRM module.

Permissions:
- List/Get: requires 'viewer' role in organization
- Create/Update: requires 'member' role in organization
- Delete: requires 'admin' role in organization
- Convert: requires 'member' role in organization
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_min_role, is_admin_or_owner
from app.models.user import User
from app.models.lead import Lead, LeadStatus, LeadSource
from app.models.contact import Contact, ContactType
from app.models.opportunity import Opportunity, OpportunityStage
from app.models.org_membership import OrgMembershipRole
from app.schemas.crm import (
    LeadCreate, LeadUpdate, LeadConvert, LeadResponse, LeadListResponse
)

router = APIRouter()


def lead_to_response(lead: Lead) -> LeadResponse:
    """Convert Lead model to response schema."""
    return LeadResponse(
        id=lead.id,
        organization_id=lead.organization_id,
        name=lead.name,
        contact_name=lead.contact_name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        website=lead.website,
        status=lead.status.value if isinstance(lead.status, LeadStatus) else lead.status,
        source=lead.source.value if isinstance(lead.source, LeadSource) else lead.source,
        owner_user_id=lead.owner_user_id,
        notes=lead.notes,
        converted_contact_id=lead.converted_contact_id,
        converted_opportunity_id=lead.converted_opportunity_id,
        created=lead.created,
        updated=lead.updated,
    )


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    organization_id: str = Query(..., description="Organization ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    owner_user_id: Optional[str] = Query(None, description="Filter by owner"),
    search: Optional[str] = Query(None, description="Search name/email/company"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List leads for an organization."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    query = select(Lead).where(Lead.organization_id == organization_id)

    # Apply filters
    if status:
        try:
            status_enum = LeadStatus(status)
            query = query.where(Lead.status == status_enum)
        except ValueError:
            pass

    if owner_user_id:
        query = query.where(Lead.owner_user_id == owner_user_id)

    if search:
        search_filter = (
            Lead.name.ilike(f"%{search}%") |
            Lead.email.ilike(f"%{search}%") |
            Lead.company.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    # Order by created desc
    query = query.order_by(Lead.created.desc())

    # Pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    leads = result.scalars().all()

    items = [lead_to_response(l) for l in leads]
    return LeadListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new lead."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    # Validate enums
    try:
        status_enum = LeadStatus(lead_data.status)
    except ValueError:
        status_enum = LeadStatus.NEW

    try:
        source_enum = LeadSource(lead_data.source)
    except ValueError:
        source_enum = LeadSource.OTHER

    lead = Lead(
        organization_id=organization_id,
        name=lead_data.name,
        contact_name=lead_data.contact_name,
        email=lead_data.email,
        phone=lead_data.phone,
        company=lead_data.company,
        website=lead_data.website,
        status=status_enum,
        source=source_enum,
        notes=lead_data.notes,
        owner_user_id=current_user.id,  # Assign to creator by default
    )

    db.add(lead)
    await db.flush()
    await db.refresh(lead)

    return lead_to_response(lead)


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a lead by ID."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id
        )
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    return lead_to_response(lead)


@router.patch("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    lead_data: LeadUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a lead."""
    membership = await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id
        )
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    # Members can only update their own leads unless admin
    if not is_admin_or_owner(membership) and lead.owner_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own leads"
        )

    # Update fields
    if lead_data.name is not None:
        lead.name = lead_data.name
    if lead_data.contact_name is not None:
        lead.contact_name = lead_data.contact_name
    if lead_data.email is not None:
        lead.email = lead_data.email
    if lead_data.phone is not None:
        lead.phone = lead_data.phone
    if lead_data.company is not None:
        lead.company = lead_data.company
    if lead_data.website is not None:
        lead.website = lead_data.website
    if lead_data.status is not None:
        try:
            lead.status = LeadStatus(lead_data.status)
        except ValueError:
            pass
    if lead_data.source is not None:
        try:
            lead.source = LeadSource(lead_data.source)
        except ValueError:
            pass
    if lead_data.notes is not None:
        lead.notes = lead_data.notes
    if lead_data.owner_user_id is not None and is_admin_or_owner(membership):
        lead.owner_user_id = lead_data.owner_user_id

    lead.updated = datetime.now(timezone.utc)
    await db.flush()

    return lead_to_response(lead)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a lead. Requires admin role."""
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.ADMIN)

    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id
        )
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    await db.delete(lead)
    await db.flush()

    return None


@router.post("/leads/{lead_id}/convert", response_model=LeadResponse)
async def convert_lead(
    lead_id: str,
    convert_data: LeadConvert,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert a lead to contact and/or opportunity.

    - If create_contact is True, creates a Contact from the lead
    - If create_opportunity is True, creates an Opportunity linked to the contact
    - Updates lead status to 'converted'
    """
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    result = await db.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id
        )
    )
    lead = result.scalar_one_or_none()

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )

    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead has already been converted"
        )

    contact_id = None
    opportunity_id = None

    # Create contact if requested
    if convert_data.create_contact:
        contact = Contact(
            organization_id=organization_id,
            name=lead.contact_name or lead.name,
            company=lead.company,
            email=lead.email,
            phone=lead.phone,
            website=lead.website,
            contact_type=ContactType.PROSPECT,
            notes=lead.notes,
        )
        db.add(contact)
        await db.flush()
        contact_id = contact.id
        lead.converted_contact_id = contact_id

    # Create opportunity if requested
    if convert_data.create_opportunity:
        opp_title = convert_data.opportunity_title or f"Opportunity from {lead.name}"
        opportunity = Opportunity(
            organization_id=organization_id,
            title=opp_title,
            related_contact_id=contact_id,
            amount=convert_data.opportunity_amount,
            stage=OpportunityStage.PROSPECTING,
            owner_user_id=lead.owner_user_id or current_user.id,
        )
        db.add(opportunity)
        await db.flush()
        opportunity_id = opportunity.id
        lead.converted_opportunity_id = opportunity_id

    # Update lead status
    lead.status = LeadStatus.CONVERTED
    lead.updated = datetime.now(timezone.utc)
    await db.flush()

    return lead_to_response(lead)
