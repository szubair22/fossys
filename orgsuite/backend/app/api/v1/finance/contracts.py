"""
Contracts API for ASC 606 revenue recognition.

Provides endpoints for:
- Contract CRUD operations
- Contract line management
- Contract activation (triggers allocation and schedule generation)

All endpoints are guarded by edition checks - returns 403 if enable_contracts=false.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract, ContractStatus
from app.models.contract_line import ContractLine, ContractLineStatus
from app.models.base import generate_id
from app.services.settings import get_finance_features
from app.services.revenue_recognition import (
    allocate_contract_transaction_price,
    generate_revenue_schedule_for_line,
)
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractListResponse,
    ContractSummary,
    ContractListSummaryResponse,
    ContractLineCreate,
    ContractLineUpdate,
    ContractLineResponse,
    ContractActivateRequest,
    ContractActivateResponse,
    ContractStatus as ContractStatusSchema,
)

router = APIRouter()


async def require_contracts_enabled(
    organization_id: str,
    db: AsyncSession
) -> None:
    """
    Verify that contracts feature is enabled for the organization.

    Raises 403 if enable_contracts=false in finance_config.
    """
    features = await get_finance_features(db, organization_id)
    if not features.get("enable_contracts", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contracts feature is not enabled for this organization. "
                   "Switch to Nonprofit edition or enable contracts in finance settings."
        )


def _contract_to_response(contract: Contract) -> ContractResponse:
    """Convert Contract model to response schema."""
    lines = [
        ContractLineResponse(
            id=line.id,
            contract_id=line.contract_id,
            description=line.description,
            product_type=line.product_type,
            recognition_pattern=line.recognition_pattern,
            start_date=line.start_date,
            end_date=line.end_date,
            quantity=line.quantity,
            unit_price=line.unit_price,
            ssp_amount=line.ssp_amount,
            allocated_transaction_price=line.allocated_transaction_price,
            revenue_account_id=line.revenue_account_id,
            deferred_revenue_account_id=line.deferred_revenue_account_id,
            status=line.status,
            sort_order=line.sort_order,
            created=line.created,
            updated=line.updated,
        )
        for line in (contract.lines or [])
    ]

    return ContractResponse(
        id=contract.id,
        organization_id=contract.organization_id,
        name=contract.name,
        description=contract.description,
        contract_number=contract.contract_number,
        customer_contact_id=contract.customer_contact_id,
        member_id=contract.member_id,
        project_id=contract.project_id,
        start_date=contract.start_date,
        end_date=contract.end_date,
        total_transaction_price=contract.total_transaction_price,
        currency=contract.currency,
        status=contract.status,
        notes=contract.notes,
        created_by_id=contract.created_by_id,
        created=contract.created,
        updated=contract.updated,
        customer_name=contract.customer_name,
        lines=lines,
    )


# ============================================================================
# CONTRACT CRUD ENDPOINTS
# ============================================================================

@router.get("", response_model=ContractListSummaryResponse)
async def list_contracts(
    organization_id: str = Query(..., description="Organization ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List contracts for an organization.

    Returns a summary view without nested lines for better performance.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    # Build query
    query = (
        select(Contract)
        .where(Contract.organization_id == organization_id)
        .options(
            selectinload(Contract.lines),
            selectinload(Contract.customer_contact),
            selectinload(Contract.member),
        )
        .order_by(Contract.created.desc())
    )

    if status_filter:
        query = query.where(Contract.status == status_filter)

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    contracts = list(result.scalars().all())

    # Count total
    count_query = select(func.count(Contract.id)).where(
        Contract.organization_id == organization_id
    )
    if status_filter:
        count_query = count_query.where(Contract.status == status_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Build summary response
    items = [
        ContractSummary(
            id=c.id,
            organization_id=c.organization_id,
            contract_number=c.contract_number,
            name=c.name,
            customer_name=c.customer_name,
            status=c.status,
            start_date=c.start_date,
            end_date=c.end_date,
            total_transaction_price=c.total_transaction_price,
            currency=c.currency,
            lines_count=len(c.lines) if c.lines else 0,
            created=c.created,
        )
        for c in contracts
    ]

    return ContractListSummaryResponse(items=items, total=total)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a single contract by ID with all lines.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(Contract)
        .where(
            and_(
                Contract.id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(
            selectinload(Contract.lines),
            selectinload(Contract.customer_contact),
            selectinload(Contract.member),
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    return _contract_to_response(contract)


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new contract with optional lines.

    Requires enable_contracts=true in organization finance settings.
    """
    import logging
    logger = logging.getLogger(__name__)

    from pydantic import ValidationError
    try:
        logger.info(f"Creating contract: org={data.organization_id}, name={data.name}, lines={len(data.lines) if data.lines else 0}")

        await require_contracts_enabled(data.organization_id, db)

        # Generate contract number if not provided
        contract_number = data.contract_number
        if not contract_number:
            # Auto-generate: CON-YYYYMMDD-XXXX
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            contract_number = f"CON-{date_str}-{generate_id()[:4].upper()}"

        # Create contract
        contract = Contract(
            id=generate_id(),
            organization_id=data.organization_id,
            contract_number=contract_number,
            name=data.name,
            description=data.description,
            customer_contact_id=data.customer_contact_id,
            member_id=data.member_id,
            project_id=data.project_id,
            start_date=data.start_date,
            end_date=data.end_date,
            total_transaction_price=data.total_transaction_price,
            currency=data.currency,
            status=ContractStatus(data.status.value) if data.status else ContractStatus.DRAFT,
            notes=data.notes,
            created_by_id=current_user.id,
        )
        db.add(contract)
        await db.flush()
        logger.info(f"Contract created with ID: {contract.id}")

        # Create lines if provided
        if data.lines:
            for i, line_data in enumerate(data.lines):
                logger.info(f"Creating line {i}: desc={line_data.description}, pattern={line_data.recognition_pattern}")
                line = ContractLine(
                    id=generate_id(),
                    contract_id=contract.id,
                    description=line_data.description,
                    product_type=line_data.product_type,
                    recognition_pattern=line_data.recognition_pattern,
                    start_date=line_data.start_date or data.start_date,
                    end_date=line_data.end_date or data.end_date,
                    quantity=line_data.quantity,
                    unit_price=line_data.unit_price,
                    ssp_amount=line_data.ssp_amount,
                    revenue_account_id=line_data.revenue_account_id,
                    deferred_revenue_account_id=line_data.deferred_revenue_account_id,
                    status=ContractLineStatus.DRAFT,
                    sort_order=line_data.sort_order or i,
                )
                db.add(line)

        await db.commit()
        logger.info(f"Contract {contract.id} committed successfully")

        # Reload with relationships
        await db.refresh(contract)
        result = await db.execute(
            select(Contract)
            .where(Contract.id == contract.id)
            .options(
                selectinload(Contract.lines),
                selectinload(Contract.customer_contact),
                selectinload(Contract.member),
            )
        )
        contract = result.scalar_one()

        return _contract_to_response(contract)
    except ValidationError as e:
        logger.exception("ContractCreate validation failed: %s", e.errors())
        raise
    except HTTPException:
        raise
    except Exception:
        logger.exception("ContractCreate failed unexpectedly")
        raise


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    data: ContractUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a contract.

    Only draft or pending contracts can be fully edited.
    Active contracts have limited editability.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(Contract)
        .where(
            and_(
                Contract.id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(selectinload(Contract.lines))
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    # Check if contract can be edited
    if contract.status in [ContractStatus.COMPLETED, ContractStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit contract with status: {contract.status.value}"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # For active contracts, limit what can be changed
    if contract.status == ContractStatus.ACTIVE:
        restricted_fields = ["start_date", "total_transaction_price", "currency"]
        for field in restricted_fields:
            if field in update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot modify {field} on an active contract"
                )

    for field, value in update_data.items():
        if field == "status" and value:
            value = ContractStatus(value.value if hasattr(value, "value") else value)
        setattr(contract, field, value)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Contract)
        .where(Contract.id == contract.id)
        .options(
            selectinload(Contract.lines),
            selectinload(Contract.customer_contact),
            selectinload(Contract.member),
        )
    )
    contract = result.scalar_one()

    return _contract_to_response(contract)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a contract.

    Only draft contracts can be deleted.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(Contract)
        .where(
            and_(
                Contract.id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    if contract.status != ContractStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft contracts can be deleted"
        )

    await db.delete(contract)
    await db.commit()


# ============================================================================
# CONTRACT ACTIVATION ENDPOINT
# ============================================================================

@router.post("/{contract_id}/activate", response_model=ContractActivateResponse)
async def activate_contract(
    contract_id: str,
    data: ContractActivateRequest,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a contract.

    This endpoint:
    1. Validates contract has lines
    2. Allocates transaction price to lines
    3. Optionally generates revenue schedules
    4. Sets contract status to ACTIVE

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(Contract)
        .where(
            and_(
                Contract.id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(selectinload(Contract.lines))
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    if contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate contract with status: {contract.status.value}"
        )

    if not contract.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract must have at least one line to activate"
        )

    # Allocate transaction price
    lines_allocated = await allocate_contract_transaction_price(contract, db)

    # Activate contract and lines
    contract.status = ContractStatus.ACTIVE
    for line in contract.lines:
        line.status = ContractLineStatus.ACTIVE

    # Generate revenue schedules if requested and rev_rec is enabled
    schedules_generated = 0
    if data.generate_schedules:
        features = await get_finance_features(db, organization_id)
        if features.get("enable_rev_rec", False):
            for line in contract.lines:
                schedule = await generate_revenue_schedule_for_line(
                    line,
                    organization_id,
                    db,
                    current_user.id
                )
                if schedule:
                    schedules_generated += 1

    await db.commit()

    message = f"Contract activated with {lines_allocated} line(s) allocated"
    if schedules_generated > 0:
        message += f" and {schedules_generated} revenue schedule(s) generated"

    return ContractActivateResponse(
        contract_id=contract.id,
        status=ContractStatusSchema(contract.status.value),
        lines_allocated=lines_allocated,
        schedules_generated=schedules_generated,
        message=message
    )


# ============================================================================
# CONTRACT LINE ENDPOINTS
# ============================================================================

@router.post("/{contract_id}/lines", response_model=ContractLineResponse, status_code=status.HTTP_201_CREATED)
async def add_contract_line(
    contract_id: str,
    data: ContractLineCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a line to an existing contract.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(Contract)
        .where(
            and_(
                Contract.id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(selectinload(Contract.lines))
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )

    if contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add lines to a contract that is not in draft or pending status"
        )

    # Determine sort order
    max_sort = max((line.sort_order for line in contract.lines), default=-1)

    line = ContractLine(
        id=generate_id(),
        contract_id=contract.id,
        description=data.description,
        product_type=data.product_type,
        recognition_pattern=data.recognition_pattern,
        start_date=data.start_date or contract.start_date,
        end_date=data.end_date or contract.end_date,
        quantity=data.quantity,
        unit_price=data.unit_price,
        ssp_amount=data.ssp_amount,
        revenue_account_id=data.revenue_account_id,
        deferred_revenue_account_id=data.deferred_revenue_account_id,
        status=ContractLineStatus.DRAFT,
        sort_order=data.sort_order if data.sort_order is not None else max_sort + 1,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)

    return ContractLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        description=line.description,
        product_type=line.product_type,
        recognition_pattern=line.recognition_pattern,
        start_date=line.start_date,
        end_date=line.end_date,
        quantity=line.quantity,
        unit_price=line.unit_price,
        ssp_amount=line.ssp_amount,
        allocated_transaction_price=line.allocated_transaction_price,
        revenue_account_id=line.revenue_account_id,
        deferred_revenue_account_id=line.deferred_revenue_account_id,
        status=line.status,
        sort_order=line.sort_order,
        created=line.created,
        updated=line.updated,
    )


@router.patch("/{contract_id}/lines/{line_id}", response_model=ContractLineResponse)
async def update_contract_line(
    contract_id: str,
    line_id: str,
    data: ContractLineUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a contract line.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(ContractLine)
        .join(Contract)
        .where(
            and_(
                ContractLine.id == line_id,
                ContractLine.contract_id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(selectinload(ContractLine.contract))
    )
    line = result.scalar_one_or_none()

    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract line not found"
        )

    if line.contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify lines on a contract that is not in draft or pending status"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = ContractLineStatus(value.value if hasattr(value, "value") else value)
        setattr(line, field, value)

    await db.commit()
    await db.refresh(line)

    return ContractLineResponse(
        id=line.id,
        contract_id=line.contract_id,
        description=line.description,
        product_type=line.product_type,
        recognition_pattern=line.recognition_pattern,
        start_date=line.start_date,
        end_date=line.end_date,
        quantity=line.quantity,
        unit_price=line.unit_price,
        ssp_amount=line.ssp_amount,
        allocated_transaction_price=line.allocated_transaction_price,
        revenue_account_id=line.revenue_account_id,
        deferred_revenue_account_id=line.deferred_revenue_account_id,
        status=line.status,
        sort_order=line.sort_order,
        created=line.created,
        updated=line.updated,
    )


@router.delete("/{contract_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract_line(
    contract_id: str,
    line_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a contract line.

    Requires enable_contracts=true in organization finance settings.
    """
    await require_contracts_enabled(organization_id, db)

    result = await db.execute(
        select(ContractLine)
        .join(Contract)
        .where(
            and_(
                ContractLine.id == line_id,
                ContractLine.contract_id == contract_id,
                Contract.organization_id == organization_id,
            )
        )
        .options(selectinload(ContractLine.contract))
    )
    line = result.scalar_one_or_none()

    if not line:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract line not found"
        )

    if line.contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete lines from a contract that is not in draft or pending status"
        )

    await db.delete(line)
    await db.commit()
