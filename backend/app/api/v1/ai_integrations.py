"""AI Integration endpoints - PocketBase compatible."""
from datetime import datetime, timezone
from typing import Optional
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.base import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.ai_integration import AIIntegration as AIIntegrationModel, AIProvider
from app.models.organization import Organization
from app.core.permissions import require_min_role, OrgMembershipRole
from app.schemas.ai_integration import AIIntegrationCreate, AIIntegrationUpdate, AIIntegrationResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()


def ai_integration_to_response(a: AIIntegrationModel) -> AIIntegrationResponse:
    return AIIntegrationResponse(
        id=a.id,
        organization=a.organization_id,
        provider=a.provider.value if a.provider else None,
        model=a.model,
        is_active=a.is_active,
        settings=a.settings,
        last_used_at=a.last_used_at,
        usage_count=a.usage_count or 0,
        created_by=a.created_by_id,
        created=a.created,
        updated=a.updated,
        expand=None,
    )


@router.get("/records", response_model=PaginatedResponse[AIIntegrationResponse])
async def list_ai_integrations(page: int = Query(1, ge=1), perPage: int = Query(30, ge=1, le=500), filter: Optional[str] = None, sort: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    query = select(AIIntegrationModel)
    if filter and "organization=" in filter:
        org_id = filter.split("organization=")[1].split("\"")[1] if '"' in filter else filter.split("organization=")[1].split()[0]
        query = query.where(AIIntegrationModel.organization_id == org_id)
    if filter and "is_active" in filter:
        if "is_active = true" in filter:
            query = query.where(AIIntegrationModel.is_active.is_(True))
        if "is_active = false" in filter:
            query = query.where(AIIntegrationModel.is_active.is_(False))

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    if sort:
        if sort.startswith("-"):
            f = sort[1:]
            if hasattr(AIIntegrationModel, f):
                query = query.order_by(getattr(AIIntegrationModel, f).desc())
        else:
            if hasattr(AIIntegrationModel, sort):
                query = query.order_by(getattr(AIIntegrationModel, sort).asc())
    else:
        query = query.order_by(AIIntegrationModel.created.desc())

    query = query.offset((page - 1) * perPage).limit(perPage)
    result = await db.execute(query)
    items = [ai_integration_to_response(a) for a in result.scalars().all()]
    return PaginatedResponse(page=page, perPage=perPage, totalItems=total_items, totalPages=ceil(total_items / perPage) if total_items else 1, items=items)


@router.post("/records", response_model=AIIntegrationResponse, status_code=status.HTTP_200_OK)
async def create_ai_integration(data: AIIntegrationCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    org_result = await db.execute(select(Organization).where(Organization.id == data.organization))
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Role enforcement: admin or owner required to create AI integration
    await require_min_role(db, current_user.id, data.organization, OrgMembershipRole.ADMIN)

    try:
        provider_enum = AIProvider(data.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid provider")

    ai = AIIntegrationModel(
        organization_id=data.organization,
        provider=provider_enum,
        api_key=data.api_key,
        model=data.model,
        is_active=data.is_active,
        settings=data.settings,
        created_by_id=current_user.id,
    )
    db.add(ai)
    await db.flush()
    return ai_integration_to_response(ai)


@router.get("/records/{integration_id}", response_model=AIIntegrationResponse)
async def get_ai_integration(integration_id: str, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    result = await db.execute(select(AIIntegrationModel).where(AIIntegrationModel.id == integration_id))
    ai = result.scalar_one_or_none()
    if ai is None:
        raise HTTPException(status_code=404, detail="AI integration not found")
    return ai_integration_to_response(ai)


@router.patch("/records/{integration_id}", response_model=AIIntegrationResponse)
async def update_ai_integration(integration_id: str, data: AIIntegrationUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(AIIntegrationModel).where(AIIntegrationModel.id == integration_id))
    ai = result.scalar_one_or_none()
    if ai is None:
        raise HTTPException(status_code=404, detail="AI integration not found")

    # Role enforcement: admin or owner for updates
    await require_min_role(db, current_user.id, ai.organization_id, OrgMembershipRole.ADMIN)

    if data.provider is not None:
        try:
            ai.provider = AIProvider(data.provider)
        except ValueError:
            pass
    if data.api_key is not None:
        ai.api_key = data.api_key
    if data.model is not None:
        ai.model = data.model
    if data.is_active is not None:
        ai.is_active = data.is_active
    if data.settings is not None:
        ai.settings = data.settings
    if data.last_used_at is not None:
        ai.last_used_at = data.last_used_at
    if data.usage_count is not None:
        ai.usage_count = data.usage_count

    ai.updated = datetime.now(timezone.utc)
    await db.flush()
    return ai_integration_to_response(ai)


@router.delete("/records/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_integration(integration_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(AIIntegrationModel).where(AIIntegrationModel.id == integration_id))
    ai = result.scalar_one_or_none()
    if ai is None:
        raise HTTPException(status_code=404, detail="AI integration not found")
    # Role enforcement: admin or owner for deletion
    await require_min_role(db, current_user.id, ai.organization_id, OrgMembershipRole.ADMIN)
    await db.delete(ai)
    await db.flush()
    return None
