"""
Meeting template endpoints for OrgSuite Governance module.

Migrated from PocketBase to FastAPI.
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.db.base import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.meeting_template import MeetingTemplate, OrgType
from app.models.meeting import MeetingType
from app.models.org_membership import OrgMembership, OrgMembershipRole
from app.core.permissions import require_min_role, OrgMembershipRole as RRole
from app.schemas.meeting_template import (
    MeetingTemplateCreate,
    MeetingTemplateUpdate,
    MeetingTemplateResponse,
    MeetingTemplateListResponse,
)

router = APIRouter()


def template_to_response(template: MeetingTemplate) -> MeetingTemplateResponse:
    """Convert MeetingTemplate model to response schema."""
    return MeetingTemplateResponse(
        id=template.id,
        organization_id=template.organization_id,
        name=template.name,
        description=template.description,
        org_type=template.org_type.value if template.org_type else None,
        default_meeting_title=template.default_meeting_title,
        default_meeting_type=template.default_meeting_type.value if template.default_meeting_type else None,
        default_agenda=template.default_agenda,
        settings=template.settings,
        is_global=template.is_global,
        created_by_id=template.created_by_id,
        created=template.created,
        updated=template.updated,
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


@router.get("", response_model=MeetingTemplateListResponse)
async def list_templates(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    org_type: Optional[str] = Query(None, description="Filter by organization type"),
    include_global: bool = Query(True, description="Include global templates"),
    page: int = Query(1, ge=1),
    perPage: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List meeting templates.

    Returns:
    - Organization-specific templates if organization_id is provided
    - Global templates if include_global is True
    - Templates filtered by org_type if provided
    """
    # Build query
    conditions = []

    if organization_id:
        # Check org access
        if not await check_org_access(organization_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this organization"
            )

        if include_global:
            conditions.append(
                or_(
                    MeetingTemplate.organization_id == organization_id,
                    MeetingTemplate.is_global == True
                )
            )
        else:
            conditions.append(MeetingTemplate.organization_id == organization_id)
    else:
        # Only global templates if no org specified
        conditions.append(MeetingTemplate.is_global == True)

    # Filter by org_type
    if org_type:
        try:
            org_type_enum = OrgType(org_type)
            conditions.append(
                or_(
                    MeetingTemplate.org_type == org_type_enum,
                    MeetingTemplate.org_type.is_(None)
                )
            )
        except ValueError:
            pass

    query = select(MeetingTemplate)
    if conditions:
        query = query.where(*conditions)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar() or 0

    # Apply pagination and sorting
    query = query.order_by(MeetingTemplate.name.asc())
    query = query.offset((page - 1) * perPage).limit(perPage)

    # Execute query
    result = await db.execute(query)
    templates = result.scalars().all()

    items = [template_to_response(t) for t in templates]

    return MeetingTemplateListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.get("/{template_id}", response_model=MeetingTemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a meeting template by ID.
    """
    result = await db.execute(
        select(MeetingTemplate).where(MeetingTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check access - global templates are accessible to all
    if not template.is_global and template.organization_id:
        if not await check_org_access(template.organization_id, current_user, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this template"
            )

    return template_to_response(template)


@router.post("", response_model=MeetingTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    organization_id: str = Query(..., description="Organization ID"),
    template_data: MeetingTemplateCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a meeting template.
    Requires org admin access.
    """
    # Role enforcement: require ADMIN for template creation
    await require_min_role(db, current_user.id, organization_id, RRole.ADMIN)

    # Parse enums
    org_type_enum = None
    if template_data.org_type:
        try:
            org_type_enum = OrgType(template_data.org_type)
        except ValueError:
            pass

    meeting_type_enum = None
    if template_data.default_meeting_type:
        try:
            meeting_type_enum = MeetingType(template_data.default_meeting_type)
        except ValueError:
            pass

    # Create template
    template = MeetingTemplate(
        organization_id=organization_id,
        name=template_data.name,
        description=template_data.description,
        org_type=org_type_enum,
        default_meeting_title=template_data.default_meeting_title,
        default_meeting_type=meeting_type_enum,
        default_agenda=template_data.default_agenda,
        settings=template_data.settings,
        is_global=False,  # Org templates are not global
        created_by_id=current_user.id,
    )

    db.add(template)
    await db.flush()

    return template_to_response(template)


@router.patch("/{template_id}", response_model=MeetingTemplateResponse)
async def update_template(
    template_id: str,
    template_data: MeetingTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a meeting template.
    Requires being creator or org admin.
    """
    result = await db.execute(
        select(MeetingTemplate).where(MeetingTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check permission
    # Role enforcement: require ADMIN unless creator
    is_creator = template.created_by_id == current_user.id
    if template.organization_id and not is_creator:
        await require_min_role(db, current_user.id, template.organization_id, RRole.ADMIN)

    # Global templates can only be modified by superadmins
    if template.is_global and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can modify global templates"
        )

    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.org_type is not None:
        try:
            template.org_type = OrgType(template_data.org_type)
        except ValueError:
            pass
    if template_data.default_meeting_title is not None:
        template.default_meeting_title = template_data.default_meeting_title
    if template_data.default_meeting_type is not None:
        try:
            template.default_meeting_type = MeetingType(template_data.default_meeting_type)
        except ValueError:
            pass
    if template_data.default_agenda is not None:
        template.default_agenda = template_data.default_agenda
    if template_data.settings is not None:
        template.settings = template_data.settings

    template.updated = datetime.now(timezone.utc)
    await db.flush()

    return template_to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a meeting template.
    Requires being creator or org admin.
    """
    result = await db.execute(
        select(MeetingTemplate).where(MeetingTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check permission
    is_creator = template.created_by_id == current_user.id
    if template.organization_id and not is_creator:
        await require_min_role(db, current_user.id, template.organization_id, RRole.ADMIN)

    # Global templates can only be deleted by superadmins
    if template.is_global and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can delete global templates"
        )

    await db.delete(template)
    await db.flush()

    return None
