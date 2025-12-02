"""
Donations endpoints for OrgSuite Finance module.

Now includes validation against organization settings for:
- Payment methods (configurable per-org)
- Default currency (configurable per-org)
"""
from datetime import datetime, timezone, date
from typing import Optional
from math import ceil
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.donation import Donation, DonationStatus, PaymentMethod
from app.models.member import Member
from app.models.contact import Contact
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.donation import (
    DonationCreate, DonationUpdate, DonationResponse,
    DonationListResponse, DonationSummary, DonorInfo
)
from app.services.settings import get_finance_config, validate_payment_method

router = APIRouter()


def donation_to_response(donation: Donation, member: Optional[Member] = None, contact: Optional[Contact] = None) -> DonationResponse:
    """Convert Donation model to DonationResponse schema."""
    # Resolve donor info
    donor = None
    if donation.member_id and member:
        donor = DonorInfo(
            id=member.id,
            name=member.name,
            email=member.email,
            type="member"
        )
    elif donation.contact_id and contact:
        donor = DonorInfo(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            type="contact"
        )
    elif donation.donor_name:
        donor = DonorInfo(
            id=None,
            name=donation.donor_name,
            email=donation.donor_email,
            type="anonymous"
        )

    return DonationResponse(
        id=donation.id,
        organization_id=donation.organization_id,
        member_id=donation.member_id,
        contact_id=donation.contact_id,
        donor_name=donation.donor_name,
        donor_email=donation.donor_email,
        donor=donor,
        amount=donation.amount,
        currency=donation.currency,
        donation_date=donation.donation_date,
        payment_method=donation.payment_method.value if donation.payment_method else None,
        payment_reference=donation.payment_reference,
        status=donation.status.value if isinstance(donation.status, DonationStatus) else donation.status,
        purpose=donation.purpose,
        campaign=donation.campaign,
        is_tax_deductible=donation.is_tax_deductible,
        receipt_number=donation.receipt_number,
        receipt_sent=donation.receipt_sent,
        notes=donation.notes,
        created_by_id=donation.created_by_id,
        created=donation.created,
        updated=donation.updated,
    )


async def check_org_access(
    org_id: str,
    user: User,
    db: AsyncSession,
    require_admin: bool = False
) -> bool:
    """Check if user has access to the organization."""
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.organization_id == org_id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active == True
        )
    )
    membership = result.scalar_one_or_none()

    if membership is None:
        return False

    if require_admin:
        return membership.role in [OrgMembershipRole.OWNER, OrgMembershipRole.ADMIN]

    return True


@router.get("/donations/summary", response_model=DonationSummary)
async def get_donations_summary(
    organization_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    campaign: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get donation summary statistics.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Build base query
    base_filter = [Donation.organization_id == organization_id]

    if start_date:
        base_filter.append(Donation.donation_date >= start_date)
    if end_date:
        base_filter.append(Donation.donation_date <= end_date)
    if campaign:
        base_filter.append(Donation.campaign == campaign)

    # Get received totals
    received_query = select(
        func.coalesce(func.sum(Donation.amount), 0).label('total'),
        func.count(Donation.id).label('count')
    ).where(
        *base_filter,
        Donation.status == DonationStatus.RECEIVED
    )
    received_result = await db.execute(received_query)
    received_row = received_result.one()

    # Get pending totals
    pending_query = select(
        func.coalesce(func.sum(Donation.amount), 0).label('total'),
        func.count(Donation.id).label('count')
    ).where(
        *base_filter,
        Donation.status == DonationStatus.PENDING
    )
    pending_result = await db.execute(pending_query)
    pending_row = pending_result.one()

    # Get pledged totals
    pledged_query = select(
        func.coalesce(func.sum(Donation.amount), 0).label('total'),
        func.count(Donation.id).label('count')
    ).where(
        *base_filter,
        Donation.status == DonationStatus.PLEDGED
    )
    pledged_result = await db.execute(pledged_query)
    pledged_row = pledged_result.one()

    # Get configured currency from finance settings
    finance_config = await get_finance_config(db, organization_id)

    return DonationSummary(
        total_received=Decimal(str(received_row.total)),
        total_pending=Decimal(str(pending_row.total)),
        total_pledged=Decimal(str(pledged_row.total)),
        count_received=received_row.count,
        count_pending=pending_row.count,
        count_pledged=pledged_row.count,
        currency=finance_config.default_currency
    )


@router.get("/donations", response_model=DonationListResponse)
async def list_donations(
    organization_id: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    campaign: Optional[str] = None,
    member_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List donations.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Base query
    query = select(Donation).where(Donation.organization_id == organization_id)

    # Apply filters
    if status_filter:
        try:
            status_enum = DonationStatus(status_filter)
            query = query.where(Donation.status == status_enum)
        except ValueError:
            pass

    if start_date:
        query = query.where(Donation.donation_date >= start_date)
    if end_date:
        query = query.where(Donation.donation_date <= end_date)
    if campaign:
        query = query.where(Donation.campaign == campaign)
    if member_id:
        query = query.where(Donation.member_id == member_id)
    if contact_id:
        query = query.where(Donation.contact_id == contact_id)

    if search:
        query = query.where(
            Donation.donor_name.ilike(f"%{search}%") |
            Donation.donor_email.ilike(f"%{search}%") |
            Donation.purpose.ilike(f"%{search}%") |
            Donation.campaign.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.offset((page - 1) * perPage).limit(perPage)
    query = query.order_by(Donation.donation_date.desc(), Donation.created.desc())

    # Execute query
    result = await db.execute(query)
    donations = result.scalars().all()

    # Build response with donor info
    items = []
    for donation in donations:
        member = None
        contact = None

        if donation.member_id:
            member_result = await db.execute(
                select(Member).where(Member.id == donation.member_id)
            )
            member = member_result.scalar_one_or_none()

        if donation.contact_id:
            contact_result = await db.execute(
                select(Contact).where(Contact.id == donation.contact_id)
            )
            contact = contact_result.scalar_one_or_none()

        items.append(donation_to_response(donation, member, contact))

    return DonationListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/donations", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    organization_id: str,
    donation_data: DonationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new donation.
    Requires org membership.

    Validates against organization settings:
    - Payment method must be in configured payment_methods list
    - Uses default_currency from settings if not specified
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to record donations"
        )

    # Get finance settings for validation
    finance_config = await get_finance_config(db, organization_id)

    # Validate donor - at least one of member_id, contact_id, or donor_name must be set
    if not donation_data.member_id and not donation_data.contact_id and not donation_data.donor_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"donor": {"message": "Must specify member, contact, or donor name"}}
        )

    # Validate member_id if provided
    member = None
    if donation_data.member_id:
        member_result = await db.execute(
            select(Member).where(
                Member.id == donation_data.member_id,
                Member.organization_id == organization_id
            )
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"member_id": {"message": "Member not found"}}
            )

    # Validate contact_id if provided
    contact = None
    if donation_data.contact_id:
        contact_result = await db.execute(
            select(Contact).where(
                Contact.id == donation_data.contact_id,
                Contact.organization_id == organization_id
            )
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"contact_id": {"message": "Contact not found"}}
            )

    # Parse status
    try:
        status_enum = DonationStatus(donation_data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": {"message": "Invalid donation status"}}
        )

    # Parse and validate payment method against settings
    payment_method_enum = None
    if donation_data.payment_method:
        # Validate against configured payment methods
        if not validate_payment_method(donation_data.payment_method, finance_config):
            # Check if it's a valid enum value anyway (backwards compatibility)
            try:
                payment_method_enum = PaymentMethod(donation_data.payment_method)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"payment_method": {"message": f"Invalid payment method. Allowed methods: {finance_config.payment_methods}"}}
                )
        else:
            try:
                payment_method_enum = PaymentMethod(donation_data.payment_method)
            except ValueError:
                # Payment method is valid per settings but not in enum - use OTHER
                payment_method_enum = PaymentMethod.OTHER

    # Use default currency from settings if not specified
    currency = donation_data.currency or finance_config.default_currency

    # Create donation
    donation = Donation(
        organization_id=organization_id,
        member_id=donation_data.member_id,
        contact_id=donation_data.contact_id,
        donor_name=donation_data.donor_name,
        donor_email=donation_data.donor_email,
        amount=donation_data.amount,
        currency=currency,
        donation_date=donation_data.donation_date,
        payment_method=payment_method_enum,
        payment_reference=donation_data.payment_reference,
        status=status_enum,
        purpose=donation_data.purpose,
        campaign=donation_data.campaign,
        is_tax_deductible=donation_data.is_tax_deductible,
        receipt_number=donation_data.receipt_number,
        receipt_sent=donation_data.receipt_sent,
        notes=donation_data.notes,
        created_by_id=current_user.id,
    )

    db.add(donation)
    await db.flush()

    return donation_to_response(donation, member, contact)


@router.get("/donations/{donation_id}", response_model=DonationResponse)
async def get_donation(
    organization_id: str,
    donation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a donation by ID.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    result = await db.execute(
        select(Donation).where(
            Donation.id == donation_id,
            Donation.organization_id == organization_id
        )
    )
    donation = result.scalar_one_or_none()

    if donation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )

    # Get donor info
    member = None
    contact = None

    if donation.member_id:
        member_result = await db.execute(
            select(Member).where(Member.id == donation.member_id)
        )
        member = member_result.scalar_one_or_none()

    if donation.contact_id:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == donation.contact_id)
        )
        contact = contact_result.scalar_one_or_none()

    return donation_to_response(donation, member, contact)


@router.patch("/donations/{donation_id}", response_model=DonationResponse)
async def update_donation(
    organization_id: str,
    donation_id: str,
    donation_data: DonationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a donation.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update donations"
        )

    result = await db.execute(
        select(Donation).where(
            Donation.id == donation_id,
            Donation.organization_id == organization_id
        )
    )
    donation = result.scalar_one_or_none()

    if donation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )

    # Update fields
    if donation_data.member_id is not None:
        if donation_data.member_id:
            member_result = await db.execute(
                select(Member).where(
                    Member.id == donation_data.member_id,
                    Member.organization_id == organization_id
                )
            )
            if not member_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"member_id": {"message": "Member not found"}}
                )
        donation.member_id = donation_data.member_id

    if donation_data.contact_id is not None:
        if donation_data.contact_id:
            contact_result = await db.execute(
                select(Contact).where(
                    Contact.id == donation_data.contact_id,
                    Contact.organization_id == organization_id
                )
            )
            if not contact_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"contact_id": {"message": "Contact not found"}}
                )
        donation.contact_id = donation_data.contact_id

    if donation_data.donor_name is not None:
        donation.donor_name = donation_data.donor_name
    if donation_data.donor_email is not None:
        donation.donor_email = donation_data.donor_email
    if donation_data.amount is not None:
        donation.amount = donation_data.amount
    if donation_data.currency is not None:
        donation.currency = donation_data.currency
    if donation_data.donation_date is not None:
        donation.donation_date = donation_data.donation_date
    if donation_data.payment_method is not None:
        try:
            donation.payment_method = PaymentMethod(donation_data.payment_method)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"payment_method": {"message": "Invalid payment method"}}
            )
    if donation_data.payment_reference is not None:
        donation.payment_reference = donation_data.payment_reference
    if donation_data.status is not None:
        try:
            donation.status = DonationStatus(donation_data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": {"message": "Invalid donation status"}}
            )
    if donation_data.purpose is not None:
        donation.purpose = donation_data.purpose
    if donation_data.campaign is not None:
        donation.campaign = donation_data.campaign
    if donation_data.is_tax_deductible is not None:
        donation.is_tax_deductible = donation_data.is_tax_deductible
    if donation_data.receipt_number is not None:
        donation.receipt_number = donation_data.receipt_number
    if donation_data.receipt_sent is not None:
        donation.receipt_sent = donation_data.receipt_sent
    if donation_data.notes is not None:
        donation.notes = donation_data.notes

    donation.updated = datetime.now(timezone.utc)
    await db.flush()

    # Get updated donor info
    member = None
    contact = None

    if donation.member_id:
        member_result = await db.execute(
            select(Member).where(Member.id == donation.member_id)
        )
        member = member_result.scalar_one_or_none()

    if donation.contact_id:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == donation.contact_id)
        )
        contact = contact_result.scalar_one_or_none()

    return donation_to_response(donation, member, contact)


@router.delete("/donations/{donation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_donation(
    organization_id: str,
    donation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a donation.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete donations"
        )

    result = await db.execute(
        select(Donation).where(
            Donation.id == donation_id,
            Donation.organization_id == organization_id
        )
    )
    donation = result.scalar_one_or_none()

    if donation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Donation not found"
        )

    await db.delete(donation)
    await db.flush()

    return None
