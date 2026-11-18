from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.entities import User, Alert
from app.schemas.alert import AlertResponse

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all security alerts for the authenticated user."""
    stmt = (
        select(Alert)
        .where(Alert.user_id == current_user.id)
        .order_by(desc(Alert.created_at))
        .limit(50)
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return [AlertResponse.model_validate(a) for a in alerts]

@router.patch("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marks an alert as read."""
    stmt = select(Alert).where((Alert.id == alert_id) & (Alert.user_id == current_user.id))
    result = await db.execute(stmt)
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_read = True
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)

@router.post("/mark-all-read")
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marks all unread alerts as read for the current user."""
    stmt = select(Alert).where((Alert.user_id == current_user.id) & (Alert.is_read == False))
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    for a in alerts:
        a.is_read = True

    await db.commit()
    return {"message": f"Marked {len(alerts)} alerts as read"}

