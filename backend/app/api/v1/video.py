import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from app.core.config import settings
from app.core.rate_limiter import inference_rate_limiter
from app.schemas.video import VideoAnalysisResponse, FacialForensicSummary, FlaggedInterval
from app.services.video_deepfake_detector import video_deepfake_detector
from app.services.video_preprocessor import VideoValidationError
from app.services.storage import storage_service

router = APIRouter()

@router.post("/analyze", response_model=VideoAnalysisResponse, dependencies=[Depends(inference_rate_limiter)])
async def analyze_video(
    file: UploadFile = File(...),
    frame_sample_rate: int = Form(3),
    extract_faces: bool = Form(True)
):
    """
    Accepts a video recording and executes multi-frame facial manipulation analysis,
    boundary seam gradient inspection, 2D FFT spectral residual analysis, and temporal stability tracking.
    """
    clean_filename = storage_service.sanitize_filename(file.filename or "")
    valid_exts = tuple(settings.ALLOWED_VIDEO_EXTENSIONS)
    if not clean_filename or not clean_filename.lower().endswith(valid_exts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format. Supported formats: {', '.join(valid_exts)}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is empty (0 bytes)."
        )

    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Video file exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # Verify magic bytes and reject dangerous executable headers
    storage_service.verify_magic_bytes(content[:32], Path(clean_filename).suffix)

    try:
        sample_fps = max(1.0, min(10.0, float(frame_sample_rate)))
        results = await video_deepfake_detector.analyze_video(
            content,
            max_frames=30,
            sample_fps=sample_fps
        )
    except VideoValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video preprocessing failed: {str(ve)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video deepfake detection failed: {str(e)}"
        )

    meta = results.get("video_metadata", {})
    return VideoAnalysisResponse(
        job_id=uuid.uuid4(),
        status="completed",
        media_type="video",
        duration_seconds=meta.get("duration_seconds", 0.0),
        fps=meta.get("fps", 30.0),
        resolution=meta.get("resolution", "unknown"),
        total_frames_sampled=results["total_frames_sampled"],
        faces_detected=results["faces_detected"],
        spatial_manipulation_score=results["spatial_manipulation_score"],
        temporal_inconsistency_score=results["temporal_inconsistency_score"],
        verdict=results["verdict"],
        confidence_score=results["model_confidence"],
        classification=results["classification"],
        calibrated_fraud_risk=results["calibrated_fraud_risk"],
        risk_level=results["risk_level"],
        inference_engine=results["inference_engine"],
        facial_forensics=FacialForensicSummary(**results["video_metrics"]),
        suspicious_timestamps=results["suspicious_timestamps"],
        flagged_intervals=[FlaggedInterval(**interval) for interval in results["flagged_intervals"]],
        explainability_summary=results["explainability_summary"],
        actionable_recommendations=results["actionable_recommendations"],
        model_limitations=results["model_limitations"],
    )
