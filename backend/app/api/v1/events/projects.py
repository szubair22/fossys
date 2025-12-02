"""
Projects API endpoints.

Endpoints:
- GET /api/v1/events/projects - List projects
- POST /api/v1/events/projects - Create project
- GET /api/v1/events/projects/{id} - Get project
- PATCH /api/v1/events/projects/{id} - Update project
- DELETE /api/v1/events/projects/{id} - Delete project

Permissions:
- List/Get: requires 'viewer' role in organization
- Create: requires 'member' role in organization
- Update/Delete: requires 'admin' role in organization
"""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_min_role, OrgMembershipRole
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
)

router = APIRouter()


def project_to_response(project: Project) -> ProjectResponse:
    """Convert Project model to response schema."""
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        status=project.status.value if project.status else "planned",
        start_date=project.start_date,
        end_date=project.end_date,
        committee_id=project.committee_id,
        owner_id=project.owner_id,
        created=project.created,
        updated=project.updated,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    organization_id: str = Query(..., description="Organization ID"),
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List projects for an organization."""
    # Role check: viewer can list
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    query = select(Project).where(Project.organization_id == organization_id)

    if status:
        try:
            status_enum = ProjectStatus(status)
            query = query.where(Project.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status filter

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    # Order by created desc
    query = query.order_by(Project.created.desc())

    # Pagination
    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    projects = result.scalars().all()

    items = [project_to_response(p) for p in projects]
    return ProjectListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project."""
    # Role check: member can create
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.MEMBER)

    # Validate status
    try:
        status_enum = ProjectStatus(project_data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {project_data.status}"
        )

    project = Project(
        organization_id=organization_id,
        name=project_data.name,
        description=project_data.description,
        status=status_enum,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        committee_id=project_data.committee_id,
        owner_id=current_user.id,
    )

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a project by ID."""
    # Role check: viewer can read
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.VIEWER)

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id
        )
    )
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project."""
    # Role check: admin can update
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.ADMIN)

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id
        )
    )
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Update fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        try:
            project.status = ProjectStatus(project_data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {project_data.status}"
            )
    if project_data.start_date is not None:
        project.start_date = project_data.start_date
    if project_data.end_date is not None:
        project.end_date = project_data.end_date
    if project_data.committee_id is not None:
        project.committee_id = project_data.committee_id

    project.updated = datetime.now(timezone.utc)
    await db.flush()

    return project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project."""
    # Role check: admin can delete
    await require_min_role(db, current_user.id, organization_id, OrgMembershipRole.ADMIN)

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id
        )
    )
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    await db.delete(project)
    await db.flush()

    return None
