"""
Journal Entry endpoints for OrgSuite Finance module.
"""
from datetime import datetime, timezone, date
from typing import Optional
from decimal import Decimal
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.journal_entry import JournalEntry, JournalEntryStatus
from app.models.journal_line import JournalLine
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.journal import (
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse,
    JournalEntryListResponse, JournalLineResponse,
    PostJournalEntryRequest, VoidJournalEntryRequest
)

router = APIRouter()


def journal_line_to_response(line: JournalLine) -> JournalLineResponse:
    """Convert JournalLine model to JournalLineResponse schema."""
    return JournalLineResponse(
        id=line.id,
        journal_entry_id=line.journal_entry_id,
        line_number=line.line_number,
        account_id=line.account_id,
        debit=line.debit,
        credit=line.credit,
        description=line.description,
        department_id=line.department_id,
        project_id=line.project_id,
        class_id=line.class_id,
        location_id=line.location_id,
        custom_dimensions=line.custom_dimensions,
        created=line.created,
        updated=line.updated,
    )


def journal_entry_to_response(entry: JournalEntry, lines_list: list = None) -> JournalEntryResponse:
    """Convert JournalEntry model to JournalEntryResponse schema.

    Args:
        entry: The journal entry model
        lines_list: Optional pre-loaded list of lines to avoid lazy loading in async context
    """
    # Use provided lines_list or try to access entry.lines (if eagerly loaded)
    entry_lines = lines_list if lines_list is not None else (entry.lines if hasattr(entry, '_sa_instance_state') and 'lines' in entry.__dict__ else [])
    lines = [journal_line_to_response(line) for line in entry_lines] if entry_lines else []
    total_debits = sum(line.debit or Decimal(0) for line in entry_lines) if entry_lines else Decimal(0)
    total_credits = sum(line.credit or Decimal(0) for line in entry_lines) if entry_lines else Decimal(0)

    return JournalEntryResponse(
        id=entry.id,
        organization_id=entry.organization_id,
        entry_number=entry.entry_number,
        entry_date=entry.entry_date,
        description=entry.description,
        notes=entry.notes,
        reference=entry.reference,
        source_type=entry.source_type,
        source_id=entry.source_id,
        status=entry.status.value if isinstance(entry.status, JournalEntryStatus) else entry.status,
        posted_at=entry.posted_at,
        posted_by_id=entry.posted_by_id,
        voided_at=entry.voided_at,
        voided_by_id=entry.voided_by_id,
        void_reason=entry.void_reason,
        created_by_id=entry.created_by_id,
        total_debits=total_debits,
        total_credits=total_credits,
        lines=lines,
        created=entry.created,
        updated=entry.updated,
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


async def generate_entry_number(org_id: str, db: AsyncSession) -> str:
    """Generate a sequential entry number for the organization."""
    result = await db.execute(
        select(func.count()).select_from(JournalEntry).where(
            JournalEntry.organization_id == org_id
        )
    )
    count = result.scalar() or 0
    return f"JE-{count + 1:06d}"


@router.get("/journal-entries", response_model=JournalEntryListResponse)
async def list_journal_entries(
    organization_id: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List journal entries.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Base query with eager loading of lines
    query = select(JournalEntry).options(
        selectinload(JournalEntry.lines)
    ).where(JournalEntry.organization_id == organization_id)

    # Apply filters
    if status_filter:
        try:
            status_enum = JournalEntryStatus(status_filter)
            query = query.where(JournalEntry.status == status_enum)
        except ValueError:
            pass

    if start_date:
        query = query.where(JournalEntry.entry_date >= start_date)

    if end_date:
        query = query.where(JournalEntry.entry_date <= end_date)

    # Count total (without eager loading)
    count_query = select(func.count()).select_from(
        select(JournalEntry).where(JournalEntry.organization_id == organization_id).subquery()
    )
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.offset((page - 1) * perPage).limit(perPage)
    query = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created.desc())

    # Execute query
    result = await db.execute(query)
    entries = result.scalars().unique().all()

    # Build response
    items = [journal_entry_to_response(e) for e in entries]

    return JournalEntryListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    organization_id: str,
    entry_data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new journal entry with lines.
    Requires org membership. Entry must be balanced (debits = credits).
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create journal entries"
        )

    # Validate all accounts exist and belong to this org
    account_ids = [line.account_id for line in entry_data.lines]
    result = await db.execute(
        select(Account).where(
            Account.id.in_(account_ids),
            Account.organization_id == organization_id,
            Account.is_active == True
        )
    )
    valid_accounts = {a.id for a in result.scalars().all()}

    invalid_accounts = set(account_ids) - valid_accounts
    if invalid_accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or inactive account IDs: {list(invalid_accounts)}"
        )

    # Generate entry number
    entry_number = await generate_entry_number(organization_id, db)

    # Create journal entry
    entry = JournalEntry(
        organization_id=organization_id,
        entry_number=entry_number,
        entry_date=entry_data.entry_date,
        description=entry_data.description,
        notes=entry_data.notes,
        reference=entry_data.reference,
        source_type=entry_data.source_type,
        source_id=entry_data.source_id,
        status=JournalEntryStatus.DRAFT,
        created_by_id=current_user.id,
    )
    db.add(entry)
    await db.flush()

    # Create journal lines
    lines_created = []
    for i, line_data in enumerate(entry_data.lines, start=1):
        line = JournalLine(
            journal_entry_id=entry.id,
            line_number=i,
            account_id=line_data.account_id,
            debit=line_data.debit or Decimal(0),
            credit=line_data.credit or Decimal(0),
            description=line_data.description,
            department_id=line_data.department_id,
            project_id=line_data.project_id,
            class_id=line_data.class_id,
            location_id=line_data.location_id,
            custom_dimensions=line_data.custom_dimensions,
        )
        db.add(line)
        # Note: Don't append to entry.lines here - it triggers lazy loading
        # The line is already linked via journal_entry_id foreign key
        lines_created.append(line)

    await db.flush()

    # Return with the lines we just created (avoiding lazy load)
    return journal_entry_to_response(entry, lines_list=lines_created)


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    organization_id: str,
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a journal entry by ID with all lines.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    result = await db.execute(
        select(JournalEntry).options(
            selectinload(JournalEntry.lines)
        ).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

    return journal_entry_to_response(entry)


@router.patch("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    organization_id: str,
    entry_id: str,
    entry_data: JournalEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a journal entry (only draft entries can be updated).
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update journal entries"
        )

    result = await db.execute(
        select(JournalEntry).options(
            selectinload(JournalEntry.lines)
        ).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

    # Only draft entries can be updated
    if entry.status != JournalEntryStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be updated"
        )

    # Update fields
    if entry_data.entry_date is not None:
        entry.entry_date = entry_data.entry_date
    if entry_data.description is not None:
        entry.description = entry_data.description
    if entry_data.notes is not None:
        entry.notes = entry_data.notes
    if entry_data.reference is not None:
        entry.reference = entry_data.reference

    entry.updated = datetime.now(timezone.utc)
    await db.flush()

    return journal_entry_to_response(entry)


@router.post("/journal-entries/{entry_id}/post", response_model=JournalEntryResponse)
async def post_journal_entry(
    organization_id: str,
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Post a journal entry (mark as posted).
    Requires org admin access. Entry must be balanced.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to post journal entries"
        )

    result = await db.execute(
        select(JournalEntry).options(
            selectinload(JournalEntry.lines)
        ).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

    # Only draft entries can be posted
    if entry.status != JournalEntryStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be posted"
        )

    # Validate entry is balanced
    total_debits = sum(line.debit or Decimal(0) for line in entry.lines)
    total_credits = sum(line.credit or Decimal(0) for line in entry.lines)

    if abs(total_debits - total_credits) > Decimal('0.01'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Journal entry is not balanced. Debits: {total_debits}, Credits: {total_credits}"
        )

    # Post the entry
    entry.status = JournalEntryStatus.POSTED
    entry.posted_at = datetime.now(timezone.utc).date()
    entry.posted_by_id = current_user.id
    entry.updated = datetime.now(timezone.utc)

    await db.flush()

    return journal_entry_to_response(entry)


@router.post("/journal-entries/{entry_id}/void", response_model=JournalEntryResponse)
async def void_journal_entry(
    organization_id: str,
    entry_id: str,
    void_data: VoidJournalEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Void a posted journal entry.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to void journal entries"
        )

    result = await db.execute(
        select(JournalEntry).options(
            selectinload(JournalEntry.lines)
        ).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

    # Only posted entries can be voided
    if entry.status != JournalEntryStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only posted journal entries can be voided"
        )

    # Void the entry
    entry.status = JournalEntryStatus.VOIDED
    entry.voided_at = datetime.now(timezone.utc).date()
    entry.voided_by_id = current_user.id
    entry.void_reason = void_data.reason
    entry.updated = datetime.now(timezone.utc)

    await db.flush()

    return journal_entry_to_response(entry)


@router.delete("/journal-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    organization_id: str,
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a journal entry (only draft entries can be deleted).
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete journal entries"
        )

    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.organization_id == organization_id
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )

    # Only draft entries can be deleted
    if entry.status != JournalEntryStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft journal entries can be deleted"
        )

    await db.delete(entry)
    await db.flush()

    return None
