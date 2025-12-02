"""
Revenue Recognition API for ASC 606.

Provides endpoints for:
- Generating revenue schedules from contracts
- Running revenue recognition (posting journal entries)
- Querying schedules and waterfall reports

All endpoints are guarded by edition checks - returns 403 if enable_rev_rec=false.
"""
from typing import Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract, ContractStatus
from app.models.contract_line import ContractLine
from app.models.revenue_schedule import (
    RevenueSchedule,
    RevenueScheduleLineStatus,
)
from app.services.settings import get_finance_features
from app.services.revenue_recognition import (
    allocate_contract_transaction_price,
    generate_revenue_schedule_for_line,
    get_due_schedule_lines,
    run_revenue_recognition,
    get_waterfall_data,
)
from app.schemas.revenue_schedule import (
    RevenueScheduleResponse,
    RevenueScheduleListResponse,
    GenerateScheduleRequest,
    GenerateScheduleResponse,
    RevRecRunRequest,
    RevRecRunResponse,
    RevRecRunLineResult,
    WaterfallResponse,
    WaterfallPeriod,
    DueScheduleLineResponse,
    DueScheduleLinesResponse,
)

router = APIRouter()


async def require_rev_rec_enabled(
    organization_id: str,
    db: AsyncSession
) -> None:
    """
    Verify that revenue recognition feature is enabled for the organization.

    Raises 403 if enable_rev_rec=false in finance_config.
    """
    features = await get_finance_features(db, organization_id)
    if not features.get("enable_rev_rec", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Revenue recognition feature is not enabled for this organization. "
                   "Switch to Nonprofit edition or enable revenue recognition in finance settings."
        )


# ============================================================================
# SCHEDULE GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate-schedules", response_model=GenerateScheduleResponse)
async def generate_schedules(
    data: GenerateScheduleRequest,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate revenue schedules for a contract or specific contract lines.

    This endpoint:
    1. Runs allocation if not already done
    2. Generates revenue schedule for each line based on recognition pattern

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(organization_id, db)

    # Determine which contract/lines to process
    contract_id = data.contract_id
    line_ids = data.contract_line_ids

    if not contract_id and not line_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either contract_id or contract_line_ids must be provided"
        )

    # If contract_id provided, load contract with lines
    if contract_id:
        contract_result = await db.execute(
            select(Contract)
            .where(
                and_(
                    Contract.id == contract_id,
                    Contract.organization_id == organization_id,
                )
            )
            .options(selectinload(Contract.lines))
        )
        contract = contract_result.scalar_one_or_none()

        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found"
            )

        if contract.status != ContractStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract must be active to generate schedules"
            )

        # Run allocation first
        await allocate_contract_transaction_price(contract, db)

        # Generate schedules for each line
        lines_to_process = contract.lines

    else:
        # Load specific lines
        lines_result = await db.execute(
            select(ContractLine)
            .join(Contract)
            .where(
                and_(
                    ContractLine.id.in_(line_ids),
                    Contract.organization_id == organization_id,
                )
            )
            .options(selectinload(ContractLine.contract))
        )
        lines_to_process = list(lines_result.scalars().all())

        if not lines_to_process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No contract lines found"
            )

    # Generate schedules
    schedules_created = 0
    lines_created = 0
    total_amount = Decimal(0)
    schedule_ids = []

    for line in lines_to_process:
        # Skip if already has a schedule
        existing = await db.execute(
            select(RevenueSchedule).where(
                RevenueSchedule.contract_line_id == line.id
            )
        )
        if existing.scalar_one_or_none():
            continue

        schedule = await generate_revenue_schedule_for_line(
            line,
            organization_id,
            db,
            current_user.id
        )

        if schedule:
            schedules_created += 1
            schedule_ids.append(schedule.id)
            total_amount += schedule.total_amount

            # Count lines
            await db.refresh(schedule, ["lines"])
            lines_created += len(schedule.lines)

    await db.commit()

    return GenerateScheduleResponse(
        schedules_created=schedules_created,
        lines_created=lines_created,
        total_amount=total_amount,
        contract_id=contract_id,
        schedule_ids=schedule_ids,
        message=f"Generated {schedules_created} schedule(s) with {lines_created} line(s)"
    )


# ============================================================================
# REVENUE RECOGNITION RUN ENDPOINT
# ============================================================================

@router.post("/run", response_model=RevRecRunResponse)
async def run_rev_rec(
    data: RevRecRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run revenue recognition for due schedule lines.

    This endpoint:
    1. Finds all schedule lines with status=planned and schedule_date <= as_of_date
    2. For each line, creates a journal entry:
       - Dr: Deferred Revenue
       - Cr: Revenue
    3. Marks schedule lines as posted

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(data.organization_id, db)

    # Run revenue recognition
    results = await run_revenue_recognition(
        db=db,
        organization_id=data.organization_id,
        as_of_date=data.as_of_date,
        posted_by_id=current_user.id,
        contract_id=data.contract_id,
        dry_run=data.dry_run
    )

    if not data.dry_run:
        await db.commit()

    # Build response
    line_results = [
        RevRecRunLineResult(
            schedule_line_id=r["schedule_line_id"],
            schedule_date=r["schedule_date"],
            amount=r["amount"],
            journal_entry_id=r.get("journal_entry_id"),
            status=r["status"]
        )
        for r in results["line_results"]
    ]

    message = f"Processed {results['lines_processed']} lines"
    if data.dry_run:
        message = f"[DRY RUN] Would process {results['lines_processed']} lines, total ${results['total_amount']}"
    else:
        message = f"Posted {results['lines_posted']} of {results['lines_processed']} lines, total ${results['total_amount']}"

    return RevRecRunResponse(
        lines_processed=results["lines_processed"],
        lines_posted=results["lines_posted"],
        total_amount=results["total_amount"],
        journal_entries_created=results["journal_entries_created"],
        journal_entry_ids=results["journal_entry_ids"],
        dry_run=data.dry_run,
        line_results=line_results,
        message=message
    )


# ============================================================================
# SCHEDULE QUERY ENDPOINTS
# ============================================================================

@router.get("/schedules", response_model=RevenueScheduleListResponse)
async def list_revenue_schedules(
    organization_id: str = Query(..., description="Organization ID"),
    contract_id: Optional[str] = Query(None, description="Filter by contract ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List revenue schedules for an organization.

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(organization_id, db)

    # Build query
    query = (
        select(RevenueSchedule)
        .where(RevenueSchedule.organization_id == organization_id)
        .options(
            selectinload(RevenueSchedule.lines),
            selectinload(RevenueSchedule.contract_line)
        )
        .order_by(RevenueSchedule.created.desc())
    )

    if contract_id:
        query = query.join(ContractLine).where(
            ContractLine.contract_id == contract_id
        )

    if status_filter:
        query = query.where(RevenueSchedule.status == status_filter)

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    schedules = list(result.scalars().all())

    # Count total
    count_query = (
        select(RevenueSchedule)
        .where(RevenueSchedule.organization_id == organization_id)
    )
    if contract_id:
        count_query = count_query.join(ContractLine).where(
            ContractLine.contract_id == contract_id
        )
    if status_filter:
        count_query = count_query.where(RevenueSchedule.status == status_filter)

    count_result = await db.execute(count_query)
    total = len(list(count_result.scalars().all()))

    # Build response
    items = []
    for schedule in schedules:
        items.append(RevenueScheduleResponse(
            id=schedule.id,
            organization_id=schedule.organization_id,
            contract_line_id=schedule.contract_line_id,
            schedule_number=schedule.schedule_number,
            description=schedule.description,
            total_amount=schedule.total_amount,
            currency=schedule.currency,
            recognition_method=schedule.recognition_method,
            status=schedule.status,
            notes=schedule.notes,
            created_by_id=schedule.created_by_id,
            created=schedule.created,
            updated=schedule.updated,
            recognized_amount=schedule.recognized_amount,
            deferred_amount=schedule.deferred_amount,
            planned_amount=schedule.planned_amount,
            lines=[],  # Simplified for list view
        ))

    return RevenueScheduleListResponse(items=items, total=total)


@router.get("/schedules/{schedule_id}", response_model=RevenueScheduleResponse)
async def get_revenue_schedule(
    schedule_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single revenue schedule with all lines.

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(organization_id, db)

    result = await db.execute(
        select(RevenueSchedule)
        .where(
            and_(
                RevenueSchedule.id == schedule_id,
                RevenueSchedule.organization_id == organization_id,
            )
        )
        .options(selectinload(RevenueSchedule.lines))
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revenue schedule not found"
        )

    return RevenueScheduleResponse.model_validate(schedule)


# ============================================================================
# DUE SCHEDULE LINES ENDPOINT
# ============================================================================

@router.get("/due-lines", response_model=DueScheduleLinesResponse)
async def list_due_schedule_lines(
    organization_id: str = Query(..., description="Organization ID"),
    as_of_date: date = Query(..., description="As-of date for due lines"),
    contract_id: Optional[str] = Query(None, description="Filter by contract ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List schedule lines that are due for recognition.

    Due lines have status=planned and schedule_date <= as_of_date.

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(organization_id, db)

    due_lines = await get_due_schedule_lines(
        db, organization_id, as_of_date, contract_id
    )

    total_amount = sum(line.amount for line in due_lines)

    items = []
    for line in due_lines:
        # Get context info
        schedule = line.schedule
        contract_line = schedule.contract_line if schedule else None
        contract = contract_line.contract if contract_line else None

        items.append(DueScheduleLineResponse(
            id=line.id,
            revenue_schedule_id=line.revenue_schedule_id,
            schedule_date=line.schedule_date,
            amount=line.amount,
            status=line.status,
            contract_line_description=contract_line.description if contract_line else None,
            contract_name=contract.name if contract else None,
            contract_number=contract.contract_number if contract else None,
        ))

    return DueScheduleLinesResponse(
        items=items,
        total=len(items),
        total_amount=total_amount,
        as_of_date=as_of_date
    )


# ============================================================================
# WATERFALL REPORT ENDPOINT
# ============================================================================

@router.get("/waterfall", response_model=WaterfallResponse)
async def get_waterfall(
    organization_id: str = Query(..., description="Organization ID"),
    from_date: date = Query(..., description="Start of date range"),
    to_date: date = Query(..., description="End of date range"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get revenue waterfall report for a date range.

    Shows planned vs posted revenue by month.

    Requires enable_rev_rec=true in organization finance settings.
    """
    await require_rev_rec_enabled(organization_id, db)

    waterfall_data = await get_waterfall_data(
        db, organization_id, from_date, to_date
    )

    # Convert to response format
    periods = [
        WaterfallPeriod(
            period=p["period"],
            period_start=p["period_start"],
            period_end=p["period_end"],
            planned_amount=p["planned_amount"],
            posted_amount=p["posted_amount"],
            deferred_amount=p["deferred_amount"],
        )
        for p in waterfall_data["periods"]
    ]

    return WaterfallResponse(
        organization_id=waterfall_data["organization_id"],
        from_date=waterfall_data["from_date"],
        to_date=waterfall_data["to_date"],
        currency=waterfall_data["currency"],
        total_planned=waterfall_data["total_planned"],
        total_posted=waterfall_data["total_posted"],
        total_deferred=waterfall_data["total_deferred"],
        periods=periods,
    )
