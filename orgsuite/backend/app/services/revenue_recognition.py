"""
Revenue Recognition Service for ASC 606.

Provides business logic for:
- Transaction price allocation across contract lines
- Revenue schedule generation (straight-line and point-in-time)
- Revenue recognition posting (creating journal entries)
- Waterfall reporting
"""
from typing import Optional, List, Tuple
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.contract import Contract, ContractStatus
from app.models.contract_line import ContractLine, ContractLineStatus, RecognitionPattern
from app.models.revenue_schedule import (
    RevenueSchedule,
    RevenueScheduleStatus,
    RevenueScheduleLine,
    RevenueScheduleLineStatus,
    RevenueRecognitionMethod,
)
from app.models.journal_entry import JournalEntry, JournalEntryStatus
from app.models.journal_line import JournalLine
from app.models.base import generate_id


async def allocate_contract_transaction_price(
    contract: Contract,
    db: AsyncSession
) -> int:
    """
    Allocate transaction price to contract lines based on standalone selling price (SSP).

    Uses the relative SSP method: allocated_amount = total_price * (line_ssp / total_ssp)

    Args:
        contract: Contract with lines loaded
        db: Database session

    Returns:
        Number of lines allocated
    """
    if not contract.lines:
        return 0

    # Calculate total SSP
    total_ssp = sum(line.ssp_amount or Decimal(0) for line in contract.lines)

    if total_ssp == 0:
        # If no SSP set, distribute equally
        equal_share = contract.total_transaction_price / len(contract.lines)
        for line in contract.lines:
            line.allocated_transaction_price = equal_share.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        await db.flush()
        return len(contract.lines)

    # Use total transaction price from contract
    total_price = contract.total_transaction_price

    # Allocate based on relative SSP
    allocated_total = Decimal(0)
    for i, line in enumerate(contract.lines):
        if i == len(contract.lines) - 1:
            # Last line gets remainder to avoid rounding errors
            line.allocated_transaction_price = total_price - allocated_total
        else:
            ratio = (line.ssp_amount or Decimal(0)) / total_ssp
            allocation = (total_price * ratio).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            line.allocated_transaction_price = allocation
            allocated_total += allocation

    await db.flush()
    return len(contract.lines)


def _generate_monthly_periods(
    start_date: date,
    end_date: date
) -> List[Tuple[date, date, date]]:
    """
    Generate monthly periods between start and end date.

    Returns list of tuples: (recognition_date, period_start, period_end)
    Recognition date is the last day of each period.
    """
    periods = []
    current = start_date.replace(day=1)  # Start of month

    while current <= end_date:
        # Period start is either start_date or first of month
        period_start = max(current, start_date)

        # Period end is either end_date or last day of month
        next_month = current + relativedelta(months=1)
        last_day = next_month - relativedelta(days=1)
        period_end = min(last_day, end_date)

        # Recognition date is end of period
        recognition_date = period_end

        periods.append((recognition_date, period_start, period_end))

        # Move to next month
        current = next_month

    return periods


async def generate_revenue_schedule_for_line(
    line: ContractLine,
    organization_id: str,
    db: AsyncSession,
    created_by_id: Optional[str] = None
) -> Optional[RevenueSchedule]:
    """
    Generate a revenue schedule for a contract line.

    For straight_line: Generate monthly schedule lines between start and end dates.
    For point_in_time: Generate a single schedule line on start date.

    Args:
        line: ContractLine with allocated_transaction_price set
        organization_id: Organization ID
        db: Database session
        created_by_id: User ID creating the schedule

    Returns:
        Created RevenueSchedule or None if no schedule needed
    """
    if not line.allocated_transaction_price:
        return None

    total_amount = line.allocated_transaction_price

    # Map recognition pattern to method
    method_map = {
        RecognitionPattern.STRAIGHT_LINE: RevenueRecognitionMethod.STRAIGHT_LINE,
        RecognitionPattern.POINT_IN_TIME: RevenueRecognitionMethod.POINT_IN_TIME,
    }
    recognition_method = method_map.get(
        line.recognition_pattern,
        RevenueRecognitionMethod.STRAIGHT_LINE
    )

    # Create the schedule
    schedule = RevenueSchedule(
        id=generate_id(),
        organization_id=organization_id,
        contract_line_id=line.id,
        schedule_number=f"SCH-{line.contract_id[:8]}-{line.id[:4]}",
        description=f"Revenue schedule for: {line.description}",
        total_amount=total_amount,
        currency=line.contract.currency if line.contract else "USD",
        recognition_method=recognition_method,
        status=RevenueScheduleStatus.PLANNED,
        created_by_id=created_by_id,
    )
    db.add(schedule)
    await db.flush()

    # Generate schedule lines based on pattern
    if line.recognition_pattern == RecognitionPattern.POINT_IN_TIME:
        # Single recognition on start date
        recognition_date = line.start_date or line.contract.start_date
        schedule_line = RevenueScheduleLine(
            id=generate_id(),
            revenue_schedule_id=schedule.id,
            schedule_date=recognition_date,
            period_start=recognition_date,
            period_end=recognition_date,
            amount=total_amount,
            status=RevenueScheduleLineStatus.PLANNED,
        )
        db.add(schedule_line)

    elif line.recognition_pattern == RecognitionPattern.STRAIGHT_LINE:
        # Monthly recognition between start and end dates
        start = line.start_date or line.contract.start_date
        end = line.end_date or line.contract.end_date

        if not end:
            # Default to 12 months if no end date
            end = start + relativedelta(months=12) - relativedelta(days=1)

        periods = _generate_monthly_periods(start, end)

        if not periods:
            return None

        # Calculate amount per period with rounding
        num_periods = len(periods)
        amount_per_period = (total_amount / num_periods).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Track total to handle rounding
        allocated = Decimal(0)

        for i, (recognition_date, period_start, period_end) in enumerate(periods):
            if i == num_periods - 1:
                # Last period gets remainder
                amount = total_amount - allocated
            else:
                amount = amount_per_period
                allocated += amount

            schedule_line = RevenueScheduleLine(
                id=generate_id(),
                revenue_schedule_id=schedule.id,
                schedule_date=recognition_date,
                period_start=period_start,
                period_end=period_end,
                amount=amount,
                status=RevenueScheduleLineStatus.PLANNED,
            )
            db.add(schedule_line)

    await db.flush()
    return schedule


async def get_due_schedule_lines(
    db: AsyncSession,
    organization_id: str,
    as_of_date: date,
    contract_id: Optional[str] = None
) -> List[RevenueScheduleLine]:
    """
    Get all schedule lines that are due for recognition.

    Due lines are those with:
    - status = PLANNED
    - schedule_date <= as_of_date

    Args:
        db: Database session
        organization_id: Organization ID to filter by
        as_of_date: Date to check against
        contract_id: Optional contract ID to filter by

    Returns:
        List of due RevenueScheduleLine objects
    """
    # Build query with joins
    query = (
        select(RevenueScheduleLine)
        .join(RevenueSchedule)
        .join(ContractLine)
        .join(Contract)
        .where(
            and_(
                RevenueScheduleLine.status == RevenueScheduleLineStatus.PLANNED,
                RevenueScheduleLine.schedule_date <= as_of_date,
                RevenueSchedule.organization_id == organization_id,
                Contract.status == ContractStatus.ACTIVE,
            )
        )
        .options(
            selectinload(RevenueScheduleLine.schedule)
            .selectinload(RevenueSchedule.contract_line)
            .selectinload(ContractLine.contract)
        )
    )

    if contract_id:
        query = query.where(Contract.id == contract_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def post_revenue_recognition(
    schedule_line: RevenueScheduleLine,
    db: AsyncSession,
    posted_by_id: str,
    entry_date: Optional[date] = None
) -> Optional[JournalEntry]:
    """
    Post revenue recognition for a single schedule line.

    Creates a journal entry:
    - Dr: Deferred Revenue Account
    - Cr: Revenue Account

    Args:
        schedule_line: The schedule line to post
        db: Database session
        posted_by_id: User ID posting the entry
        entry_date: Date for journal entry (defaults to schedule_date)

    Returns:
        Created JournalEntry or None if posting failed
    """
    # Load related data
    schedule = schedule_line.schedule
    contract_line = schedule.contract_line
    contract = contract_line.contract

    # Validate accounts are set
    if not contract_line.revenue_account_id or not contract_line.deferred_revenue_account_id:
        return None

    # Create journal entry
    je_date = entry_date or schedule_line.schedule_date
    journal_entry = JournalEntry(
        id=generate_id(),
        organization_id=schedule.organization_id,
        entry_number=f"RR-{schedule_line.id[:8]}",
        entry_date=je_date,
        description=f"Revenue recognition: {contract.name} - {contract_line.description}",
        reference=f"Contract: {contract.contract_number or contract.id}",
        source_type="revenue_schedule",
        source_id=schedule_line.id,
        status=JournalEntryStatus.POSTED,
        posted_at=je_date,
        posted_by_id=posted_by_id,
        created_by_id=posted_by_id,
    )
    db.add(journal_entry)
    await db.flush()

    # Create debit line (Deferred Revenue - liability decrease)
    debit_line = JournalLine(
        id=generate_id(),
        journal_entry_id=journal_entry.id,
        line_number=1,
        account_id=contract_line.deferred_revenue_account_id,
        debit=schedule_line.amount,
        credit=Decimal(0),
        description=f"Deferred revenue release: {contract_line.description}",
    )
    db.add(debit_line)

    # Create credit line (Revenue - income increase)
    credit_line = JournalLine(
        id=generate_id(),
        journal_entry_id=journal_entry.id,
        line_number=2,
        account_id=contract_line.revenue_account_id,
        debit=Decimal(0),
        credit=schedule_line.amount,
        description=f"Revenue recognized: {contract_line.description}",
    )
    db.add(credit_line)

    # Update schedule line status
    schedule_line.status = RevenueScheduleLineStatus.POSTED
    schedule_line.journal_entry_id = journal_entry.id
    schedule_line.posted_at = je_date
    schedule_line.posted_by_id = posted_by_id

    # Check if all lines in schedule are posted
    await db.flush()
    await db.refresh(schedule, ["lines"])

    all_posted = all(
        line.status in [RevenueScheduleLineStatus.POSTED, RevenueScheduleLineStatus.CANCELLED]
        for line in schedule.lines
    )
    if all_posted:
        schedule.status = RevenueScheduleStatus.COMPLETED
    else:
        schedule.status = RevenueScheduleStatus.IN_PROGRESS

    await db.flush()
    return journal_entry


async def run_revenue_recognition(
    db: AsyncSession,
    organization_id: str,
    as_of_date: date,
    posted_by_id: str,
    contract_id: Optional[str] = None,
    dry_run: bool = False
) -> dict:
    """
    Run revenue recognition for all due schedule lines.

    Args:
        db: Database session
        organization_id: Organization ID
        as_of_date: Recognize revenue due on or before this date
        posted_by_id: User ID posting the entries
        contract_id: Optional contract ID to filter by
        dry_run: If True, don't actually post, just return preview

    Returns:
        Dict with results:
        - lines_processed: int
        - lines_posted: int
        - total_amount: Decimal
        - journal_entries_created: int
        - journal_entry_ids: List[str]
        - line_results: List[dict]
    """
    # Get due schedule lines
    due_lines = await get_due_schedule_lines(
        db, organization_id, as_of_date, contract_id
    )

    results = {
        "lines_processed": len(due_lines),
        "lines_posted": 0,
        "total_amount": Decimal(0),
        "journal_entries_created": 0,
        "journal_entry_ids": [],
        "line_results": [],
    }

    for schedule_line in due_lines:
        line_result = {
            "schedule_line_id": schedule_line.id,
            "schedule_date": schedule_line.schedule_date,
            "amount": schedule_line.amount,
            "journal_entry_id": None,
            "status": "skipped",
        }

        if dry_run:
            line_result["status"] = "would_post"
            results["total_amount"] += schedule_line.amount
        else:
            # Load relationships for posting
            await db.refresh(schedule_line, ["schedule"])
            await db.refresh(schedule_line.schedule, ["contract_line"])
            await db.refresh(schedule_line.schedule.contract_line, ["contract"])

            journal_entry = await post_revenue_recognition(
                schedule_line, db, posted_by_id
            )

            if journal_entry:
                line_result["journal_entry_id"] = journal_entry.id
                line_result["status"] = "posted"
                results["lines_posted"] += 1
                results["total_amount"] += schedule_line.amount
                results["journal_entries_created"] += 1
                results["journal_entry_ids"].append(journal_entry.id)
            else:
                line_result["status"] = "failed"

        results["line_results"].append(line_result)

    return results


async def get_waterfall_data(
    db: AsyncSession,
    organization_id: str,
    from_date: date,
    to_date: date
) -> dict:
    """
    Get revenue waterfall data for a date range.

    Groups schedule lines by month showing planned vs posted amounts.

    Args:
        db: Database session
        organization_id: Organization ID
        from_date: Start of date range
        to_date: End of date range

    Returns:
        Dict with waterfall data including periods and totals
    """
    # Query all schedule lines in the date range
    query = (
        select(RevenueScheduleLine)
        .join(RevenueSchedule)
        .where(
            and_(
                RevenueSchedule.organization_id == organization_id,
                RevenueScheduleLine.schedule_date >= from_date,
                RevenueScheduleLine.schedule_date <= to_date,
                RevenueScheduleLine.status != RevenueScheduleLineStatus.CANCELLED,
            )
        )
        .order_by(RevenueScheduleLine.schedule_date)
    )

    result = await db.execute(query)
    schedule_lines = list(result.scalars().all())

    # Group by month
    periods = {}
    total_planned = Decimal(0)
    total_posted = Decimal(0)

    for line in schedule_lines:
        # Get period key (YYYY-MM)
        period_key = line.schedule_date.strftime("%Y-%m")
        period_start = line.schedule_date.replace(day=1)
        next_month = period_start + relativedelta(months=1)
        period_end = next_month - relativedelta(days=1)

        if period_key not in periods:
            periods[period_key] = {
                "period": period_key,
                "period_start": period_start,
                "period_end": period_end,
                "planned_amount": Decimal(0),
                "posted_amount": Decimal(0),
            }

        if line.status == RevenueScheduleLineStatus.PLANNED:
            periods[period_key]["planned_amount"] += line.amount
            total_planned += line.amount
        elif line.status == RevenueScheduleLineStatus.POSTED:
            periods[period_key]["posted_amount"] += line.amount
            total_posted += line.amount

    # Sort periods by key
    sorted_periods = [
        periods[k] for k in sorted(periods.keys())
    ]

    # Calculate deferred amounts
    for period in sorted_periods:
        period["deferred_amount"] = period["planned_amount"]

    return {
        "organization_id": organization_id,
        "from_date": from_date,
        "to_date": to_date,
        "currency": "USD",
        "total_planned": total_planned,
        "total_posted": total_posted,
        "total_deferred": total_planned,
        "periods": sorted_periods,
    }
