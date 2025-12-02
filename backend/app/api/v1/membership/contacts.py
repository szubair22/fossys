"""
Contact endpoints for OrgSuite Membership module.
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
from app.models.contact import Contact, ContactType
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse
)

router = APIRouter()


def contact_to_response(contact: Contact) -> ContactResponse:
    """Convert Contact model to ContactResponse schema."""
    # Parse name into first/last for frontend compatibility
    name_parts = (contact.name or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else None
    last_name = name_parts[1] if len(name_parts) > 1 else None

    return ContactResponse(
        id=contact.id,
        organization_id=contact.organization_id,
        name=contact.name,
        company=contact.company,
        company_name=contact.company,  # Alias for frontend
        first_name=first_name,
        last_name=last_name,
        email=contact.email,
        phone=contact.phone,
        website=contact.website,
        address=contact.address,
        city=contact.city,
        state=contact.state,
        postal_code=contact.postal_code,
        country=contact.country,
        contact_type=contact.contact_type.value if isinstance(contact.contact_type, ContactType) else contact.contact_type,
        is_active=contact.is_active,
        tax_id=contact.tax_id,
        notes=contact.notes,
        created=contact.created,
        updated=contact.updated,
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


@router.get("/contacts", response_model=ContactListResponse)
async def list_contacts(
    organization_id: str,
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    contact_type_filter: Optional[str] = Query(None, alias="contact_type"),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List contacts of an organization.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    # Base query
    query = select(Contact).where(Contact.organization_id == organization_id)

    # Apply filters
    if contact_type_filter:
        try:
            type_enum = ContactType(contact_type_filter)
            query = query.where(Contact.contact_type == type_enum)
        except ValueError:
            pass

    if is_active is not None:
        query = query.where(Contact.is_active == is_active)

    if search:
        query = query.where(
            Contact.name.ilike(f"%{search}%") |
            Contact.company.ilike(f"%{search}%") |
            Contact.email.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    query = query.order_by(Contact.name.asc())

    # Execute query
    result = await db.execute(query)
    contacts = result.scalars().all()

    # Build response
    items = [contact_to_response(c) for c in contacts]

    return ContactListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    organization_id: str,
    contact_data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new contact.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add contacts to this organization"
        )

    # Parse contact type (handle case-insensitivity)
    try:
        type_value = contact_data.contact_type.lower() if contact_data.contact_type else "other"
        type_enum = ContactType(type_value)
    except ValueError:
        type_enum = ContactType.OTHER

    # Create contact - use helper methods to handle frontend field names
    contact = Contact(
        organization_id=organization_id,
        name=contact_data.get_full_name(),
        company=contact_data.get_company(),
        email=contact_data.email,
        phone=contact_data.phone,
        website=contact_data.website,
        address=contact_data.address,
        city=contact_data.city,
        state=contact_data.state,
        postal_code=contact_data.postal_code,
        country=contact_data.country,
        contact_type=type_enum,
        is_active=contact_data.is_active,
        tax_id=contact_data.tax_id,
        notes=contact_data.notes,
    )

    db.add(contact)
    await db.flush()

    return contact_to_response(contact)


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    organization_id: str,
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a contact by ID.
    Requires org membership.
    """
    # Check access
    if not await check_org_access(organization_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )

    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == organization_id
        )
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    return contact_to_response(contact)


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    organization_id: str,
    contact_id: str,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a contact.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update contacts"
        )

    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == organization_id
        )
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Update fields
    if contact_data.name is not None:
        contact.name = contact_data.name
    if contact_data.company is not None:
        contact.company = contact_data.company
    if contact_data.email is not None:
        contact.email = contact_data.email
    if contact_data.phone is not None:
        contact.phone = contact_data.phone
    if contact_data.website is not None:
        contact.website = contact_data.website
    if contact_data.address is not None:
        contact.address = contact_data.address
    if contact_data.city is not None:
        contact.city = contact_data.city
    if contact_data.state is not None:
        contact.state = contact_data.state
    if contact_data.postal_code is not None:
        contact.postal_code = contact_data.postal_code
    if contact_data.country is not None:
        contact.country = contact_data.country
    if contact_data.contact_type is not None:
        try:
            contact.contact_type = ContactType(contact_data.contact_type.lower())
        except ValueError:
            pass
    if contact_data.is_active is not None:
        contact.is_active = contact_data.is_active
    if contact_data.tax_id is not None:
        contact.tax_id = contact_data.tax_id
    if contact_data.notes is not None:
        contact.notes = contact_data.notes

    contact.updated = datetime.now(timezone.utc)
    await db.flush()

    return contact_to_response(contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    organization_id: str,
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a contact.
    Requires org admin access.
    """
    # Check admin access
    if not await check_org_access(organization_id, current_user, db, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete contacts"
        )

    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == organization_id
        )
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    await db.delete(contact)
    await db.flush()

    return None
