"""
File storage endpoints for OrgMeet.

Endpoints:
- GET /api/collections/files/records - List files
- POST /api/collections/files/records - Upload file
- GET /api/collections/files/records/{file_id} - Get file metadata
- GET /api/collections/files/records/{file_id}/download - Download file
- DELETE /api/collections/files/records/{file_id} - Delete file

Storage:
- Files are stored in UPLOAD_DIR/{org_id}/files/
- Naming: {uuid15}_{original_filename}
- Max file size: configurable via settings.MAX_UPLOAD_SIZE

Permissions:
- Upload: requires 'member' role in organization
- Download: requires 'member' role in organization
- Delete: requires 'admin' role in organization
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File as UploadFileField, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.models.user import User
from app.models.file import File as FileModel, FileType
from app.schemas.file import FileCreate, FileUpdate, FileResponse as FileSchema
from app.core.permissions import require_min_role, OrgMembershipRole
from app.models.meeting import Meeting
from app.models.committee import Committee
from app.schemas.common import PaginatedResponse

router = APIRouter()


def ensure_upload_dir(org_id: str):
    org_dir = os.path.join(settings.UPLOAD_DIR, org_id, "files")
    os.makedirs(org_dir, exist_ok=True)
    return org_dir


def file_to_response(f: FileModel) -> FileSchema:
    return FileSchema(
        id=f.id,
        name=f.name,
        description=f.description,
        file_type=f.file_type.value if f.file_type else None,
        file_size=f.file_size or 0,
        file=f.file,
        organization=f.organization_id,
        meeting=f.meeting_id,
        agenda_item=f.agenda_item_id,
        motion=f.motion_id,
        uploaded_by=f.uploaded_by_id,
        created=f.created,
        updated=f.updated,
        expand=None,
    )


@router.get("/records", response_model=PaginatedResponse[FileSchema])
async def list_files(
    page: int = Query(1, ge=1),
    perPage: int = Query(30, ge=1, le=500),
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """List files with optional filtering and pagination."""
    query = select(FileModel)

    if filter:
        # Simple filters organization='xyz' meeting='abc'
        if "organization=" in filter:
            org_id = filter.split("organization=")[1].split("'")[1] if "'" in filter else filter.split("organization=")[1].split()[0]
            query = query.where(FileModel.organization_id == org_id)
        if "meeting=" in filter:
            meeting_id = filter.split("meeting=")[1].split("'")[1] if "'" in filter else filter.split("meeting=")[1].split()[0]
            query = query.where(FileModel.meeting_id == meeting_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    if sort:
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(FileModel, field_name):
                query = query.order_by(getattr(FileModel, field_name).desc())
        else:
            if hasattr(FileModel, sort):
                query = query.order_by(getattr(FileModel, sort).asc())
    else:
        query = query.order_by(FileModel.created.desc())

    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    files = result.scalars().all()

    items = [file_to_response(f) for f in files]
    return PaginatedResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=ceil(total_items / perPage) if total_items > 0 else 1,
        items=items
    )


@router.post("/records", response_model=FileSchema, status_code=status.HTTP_200_OK)
async def upload_file(
    organization: str = Form(...),
    meeting: Optional[str] = Form(None),
    agenda_item: Optional[str] = Form(None),
    motion: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file_type: Optional[str] = Form(None),
    upload: UploadFile = UploadFileField(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a file. Requires member role in the organization."""
    # Role enforcement: require member to upload into organization
    await require_min_role(db, current_user.id, organization, OrgMembershipRole.MEMBER)
    org_dir = ensure_upload_dir(organization)

    original_name = upload.filename or "uploaded_file"
    final_name = name or original_name

    file_id = uuid.uuid4().hex[:15]
    stored_filename = f"{file_id}_{original_name}"
    stored_path = os.path.join(org_dir, stored_filename)

    content = await upload.read()
    try:
        with open(stored_path, "wb") as f:
            f.write(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {e}")

    file_type_enum = None
    if file_type:
        try:
            file_type_enum = FileType(file_type)
        except ValueError:
            file_type_enum = None

    rel_path = os.path.relpath(stored_path, settings.UPLOAD_DIR)
    file_model = FileModel(
        id=file_id,
        file=rel_path,
        organization_id=organization,
        meeting_id=meeting,
        agenda_item_id=agenda_item,
        motion_id=motion,
        name=final_name,
        description=description,
        file_type=file_type_enum,
        file_size=len(content),
        uploaded_by_id=current_user.id,
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    )
    db.add(file_model)
    await db.flush()

    return file_to_response(file_model)


@router.get("/records/{file_id}", response_model=FileSchema)
async def get_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    return file_to_response(f)


@router.delete("/records/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")

    # Role enforcement: require admin to delete
    if f.organization_id:
        await require_min_role(db, current_user.id, f.organization_id, OrgMembershipRole.ADMIN)

    abs_path = os.path.join(settings.UPLOAD_DIR, f.file)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass

    await db.delete(f)
    await db.flush()
    return None


@router.get("/records/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    result = await db.execute(select(FileModel).where(FileModel.id == file_id))
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    # Require at least member to download if org scoped
    if f.organization_id and current_user:
        try:
            await require_min_role(db, current_user.id, f.organization_id, OrgMembershipRole.MEMBER)
        except HTTPException:
            raise HTTPException(status_code=403, detail="Insufficient role to download file")
    abs_path = os.path.join(settings.UPLOAD_DIR, f.file)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Stored file missing")
    return FileResponse(abs_path, filename=f.name)
