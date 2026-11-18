from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.entities import User, Scan, ScanResult, RiskReport
from app.schemas.alert import AnalyticsOverview

router = APIRouter()

@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes real-time cybersecurity metrics across all user scans.
    """
    # 1. Total Scans
    stmt_total = select(func.count(Scan.id)).where(Scan.user_id == current_user.id)
    total_scans = (await db.execute(stmt_total)).scalar_one()

    # 2. Audio vs Video vs Multimodal Scans
    stmt_audio = select(func.count(Scan.id)).where((Scan.user_id == current_user.id) & (Scan.media_type == "audio"))
    audio_scans = (await db.execute(stmt_audio)).scalar_one()

    stmt_video = select(func.count(Scan.id)).where((Scan.user_id == current_user.id) & (Scan.media_type == "video"))
    video_scans = (await db.execute(stmt_video)).scalar_one()

    stmt_multi = select(func.count(Scan.id)).where((Scan.user_id == current_user.id) & (Scan.media_type == "multimodal"))
    multimodal_scans = (await db.execute(stmt_multi)).scalar_one()

    # 3. Scans with Reports
    stmt_reports = (
        select(RiskReport)
        .join(Scan, RiskReport.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
    )
    reports = (await db.execute(stmt_reports)).scalars().all()

    threats_detected = sum(1 for r in reports if r.composite_risk_score >= 50.0)
    clean_scans = total_scans - threats_detected

    avg_risk = 0.0
    if reports:
        avg_risk = round(sum(r.composite_risk_score for r in reports) / len(reports), 1)

    active_threat_level = "LOW"
    if avg_risk > 65.0 or threats_detected >= 3:
        active_threat_level = "ELEVATED"
    elif avg_risk > 40.0 or threats_detected >= 1:
        active_threat_level = "MODERATE"

    # 4. Recent activity log
    stmt_recent = (
        select(Scan)
        .where(Scan.user_id == current_user.id)
        .options(selectinload(Scan.risk_report))
        .order_by(desc(Scan.created_at))
        .limit(5)
    )
    recent_scans = (await db.execute(stmt_recent)).scalars().all()
    recent_activity = [
        {
            "id": s.id,
            "title": s.title,
            "media_type": s.media_type,
            "created_at": s.created_at.isoformat(),
            "risk_score": s.risk_report.composite_risk_score if s.risk_report else 0.0,
            "status": s.status
        }
        for s in recent_scans
    ]

    return AnalyticsOverview(
        total_scans=total_scans,
        audio_scans=audio_scans,
        video_scans=video_scans,
        multimodal_scans=multimodal_scans,
        threats_detected=threats_detected,
        clean_scans=clean_scans,
        average_risk_score=avg_risk,
        active_threat_level=active_threat_level,
        recent_activity=recent_activity
    )

@router.get("/evaluation-metrics")
async def get_evaluation_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Returns empirical model performance metrics:
    Precision, Recall, F1-Score, False Positive Rate (FPR), and latency benchmarks
    measured across audio and video detection pipelines.
    """
    from app.services.evaluator import model_evaluator
    return await model_evaluator.run_benchmark_evaluation()


