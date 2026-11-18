import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import Optional
from app.core.config import settings
from app.core.rate_limiter import inference_rate_limiter
from app.services.storage import storage_service
from app.schemas.multimodal import (
    MultimodalAnalysisResponse,
    MultimodalBreakdown,
    MultimodalFusionRequest,
    TimelineAnomaly,
    SyncMetrics,
)
from app.services.multimodal_service import multimodal_service

router = APIRouter()

@router.post("/analyze", response_model=MultimodalAnalysisResponse, dependencies=[Depends(inference_rate_limiter)])
async def analyze_multimodal(
    file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
    audio_file: Optional[UploadFile] = File(None),
    analysis_depth: str = Form("standard")
):
    """
    Executes end-to-end multimodal deepfake detection:
    Combines audio voice synthesis forensics, video facial boundary analysis,
    and audio-visual lip-sync cross-correlation into a single explainable risk report.
    Supports separate or single media stream uploads.
    """
    v_bytes = None
    a_bytes = None
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Handle single file parameter
    if file is not None:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes).")
        if len(content) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds maximum size limit.")
        clean_name = storage_service.sanitize_filename(file.filename or "")
        ext = Path(clean_name).suffix.lower()
        storage_service.verify_magic_bytes(content[:32], ext)
        if ext in settings.ALLOWED_VIDEO_EXTENSIONS:
            v_bytes = content
        elif ext in settings.ALLOWED_AUDIO_EXTENSIONS:
            a_bytes = content
        else:
            v_bytes = content

    # Handle explicit video_file
    if video_file is not None:
        content = await video_file.read()
        if len(content) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded video file is empty (0 bytes).")
        if len(content) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Video file exceeds maximum size limit.")
        clean_name = storage_service.sanitize_filename(video_file.filename or "")
        storage_service.verify_magic_bytes(content[:32], Path(clean_name).suffix)
        v_bytes = content

    # Handle explicit audio_file
    if audio_file is not None:
        content = await audio_file.read()
        if len(content) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio file is empty (0 bytes).")
        if len(content) > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file exceeds maximum size limit.")
        clean_name = storage_service.sanitize_filename(audio_file.filename or "")
        storage_service.verify_magic_bytes(content[:32], Path(clean_name).suffix)
        a_bytes = content

    if v_bytes is None and a_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one media stream (video or audio) must be provided for multimodal analysis."
        )

    try:
        report = await multimodal_service.analyze_multimodal(
            video_input=v_bytes,
            audio_input=a_bytes
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimodal risk assessment failed: {str(e)}"
        )

    sync_data = report.get("sync_metrics")
    sync_obj = SyncMetrics(**sync_data) if sync_data else None

    return MultimodalAnalysisResponse(
        job_id=uuid.uuid4(),
        media_type="multimodal",
        verdict=report["verdict"],
        risk_category=report["risk_category"],
        composite_risk_score=report["composite_risk_score"],
        confidence_score=report["confidence_score"],
        summary_explanation=report["summary_explanation"],
        breakdown=MultimodalBreakdown(**report["breakdown"]),
        sync_metrics=sync_obj,
        suspicious_timestamps=report["suspicious_timestamps"],
        timeline_anomalies=[TimelineAnomaly(**item) for item in report["timeline_anomalies"]],
        actionable_recommendations=report["actionable_recommendations"],
        model_limitations=report["model_limitations"],
    )

@router.post("/fuse", response_model=MultimodalAnalysisResponse)
async def fuse_multimodal_results(
    request: MultimodalFusionRequest
):
    """
    Fuses precomputed unimodal audio and video model outputs
    using transparent Bayesian Dempster-Shafer formulation with cross-modal conflict penalties.
    """
    try:
        report = multimodal_service.fuse_evidence(
            audio_result=request.audio_result,
            video_result=request.video_result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimodal evidence fusion failed: {str(e)}"
        )

    sync_data = report.get("sync_metrics")
    sync_obj = SyncMetrics(**sync_data) if sync_data else None

    return MultimodalAnalysisResponse(
        job_id=uuid.uuid4(),
        media_type="multimodal",
        verdict=report["verdict"],
        risk_category=report["risk_category"],
        composite_risk_score=report["composite_risk_score"],
        confidence_score=report["confidence_score"],
        summary_explanation=report["summary_explanation"],
        breakdown=MultimodalBreakdown(**report["breakdown"]),
        sync_metrics=sync_obj,
        suspicious_timestamps=report["suspicious_timestamps"],
        timeline_anomalies=[TimelineAnomaly(**item) for item in report["timeline_anomalies"]],
        actionable_recommendations=report["actionable_recommendations"],
        model_limitations=report["model_limitations"],
    )
