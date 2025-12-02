"""
Chart of Accounts endpoints for OrgSuite Finance module.
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
from app.models.account import Account, AccountType, AccountSubType
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.account import (
    AccountCreate, AccountUpdate, AccountResponse, AccountListResponse
)

router = APIRouter()


def account_to_response(account: Account) -> AccountResponse:
    """Convert Account model to AccountResponse schema."""
    return AccountResponse(
        id=account.id,
        organization_id=account.organization_id,
        code=account.code,
        name=account.name,
        description=account.description,
        account_type=account.account_type.value if isinstance(account.account_type, AccountType) else account.account_type,
        account_subtype=account.account_subtype.value if isinstance(account.account_subtype, AccountSubType) else account.account_subtype,
        parent_id=account.parent_id,
        display_order=account.display_order,
        is_active=account.is_active,
        is_system=account.is_system,
        created=account.created,
        updated=account.updated,
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


@router.get("/accounts", response_model=AccountListResponse)
async def list_accounts(
    organization_id: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    account_type_filter: Optional[str] = Query(None, alias="account_type"),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List accounts in the chart of accounts.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Base query
    query = select(Account).where(Account.organization_id == organization_id)

    # Apply filters
    if account_type_filter:
        try:
            type_enum = AccountType(account_type_filter)
            query = query.where(Account.account_type == type_enum)
        except ValueError:
            pass

    if is_active is not None:
        query = query.where(Account.is_active == is_active)

    if search:
        query = query.where(
            Account.code.ilike(f"%{search}%") |
            Account.name.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.offset((page - 1) * perPage).limit(perPage)
    query = query.order_by(Account.code.asc())

    # Execute query
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Build response
    items = [account_to_response(a) for a in accounts]

    return AccountListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    organization_id: str,
    account_data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new account.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage chart of accounts"
        )

    # Check if code already exists
    result = await db.execute(
        select(Account).where(
            Account.organization_id == organization_id,
            Account.code == account_data.code
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": {"message": "Account code already exists"}}
        )

    # Parse account type (handle case-insensitivity)
    try:
        type_value = account_data.account_type.lower() if account_data.account_type else None
        if not type_value:
            raise ValueError("Account type is required")
        type_enum = AccountType(type_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"account_type": {"message": "Invalid account type"}}
        )

    # Parse account subtype (handle case-insensitivity)
    subtype_enum = None
    if account_data.account_subtype:
        try:
            subtype_enum = AccountSubType(account_data.account_subtype.lower())
        except ValueError:
            pass  # Invalid subtype is okay, just ignore

    # Create account
    account = Account(
        organization_id=organization_id,
        code=account_data.code,
        name=account_data.name,
        description=account_data.description,
        account_type=type_enum,
        account_subtype=subtype_enum,
        parent_id=account_data.parent_id,
        display_order=account_data.display_order,
        is_active=account_data.is_active,
    )

    db.add(account)
    await db.flush()

    return account_to_response(account)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    organization_id: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an account by ID.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == organization_id
        )
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return account_to_response(account)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    organization_id: str,
    account_id: str,
    account_data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an account.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage chart of accounts"
        )

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == organization_id
        )
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Cannot update system accounts
    if account.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system accounts"
        )

    # Update fields
    if account_data.code is not None and account_data.code != account.code:
        # Check if new code already exists
        code_check = await db.execute(
            select(Account).where(
                Account.organization_id == organization_id,
                Account.code == account_data.code
            )
        )
        if code_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": {"message": "Account code already exists"}}
            )
        account.code = account_data.code

    if account_data.name is not None:
        account.name = account_data.name
    if account_data.description is not None:
        account.description = account_data.description
    if account_data.account_type is not None:
        try:
            account.account_type = AccountType(account_data.account_type.lower())
        except ValueError:
            pass
    if account_data.account_subtype is not None:
        try:
            account.account_subtype = AccountSubType(account_data.account_subtype.lower())
        except ValueError:
            pass
    if account_data.parent_id is not None:
        account.parent_id = account_data.parent_id
    if account_data.display_order is not None:
        account.display_order = account_data.display_order
    if account_data.is_active is not None:
        account.is_active = account_data.is_active

    account.updated = datetime.now(timezone.utc)
    await db.flush()

    return account_to_response(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    organization_id: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an account.
    Requires org admin access. Cannot delete accounts with journal lines.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage chart of accounts"
        )

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == organization_id
        )
    )
    account = result.scalar_one_or_none()

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Cannot delete system accounts
    if account.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system accounts"
        )

    # Check if account has journal lines (would fail due to RESTRICT)
    if account.journal_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete account with existing journal entries"
        )

    await db.delete(account)
    await db.flush()

    return None
