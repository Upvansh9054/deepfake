from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.api.v1.auth import get_current_user, require_roles
from app.models.entities import User
from app.services.retention import retention_service

router = APIRouter()

@router.get("/status")
async def get_retention_status(
    days: Optional[int] = Query(None, ge=1, le=3650, description="Hypothetical retention period in days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current data retention metrics, storage disk consumption,
    and the volume of scan assets eligible for lifecycle purge.
    """
    return await retention_service.get_retention_status(db, retention_days=days)

@router.post("/purge")
async def purge_expired_data(
    retention_days: int = Query(30, ge=1, le=3650, description="Purge scans older than this number of days"),
    admin_user: User = Depends(require_roles(["admin", "user"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes an administrative data retention purge.
    Permanently unlinks physical media files from disk and removes database records older than retention_days.
    Requires 'admin' role.
    """
    return await retention_service.purge_expired_records(
        db,
        retention_days=retention_days,
        admin_user_id=admin_user.id
    )

