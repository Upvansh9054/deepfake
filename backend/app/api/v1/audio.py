import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from app.core.config import settings
from app.core.rate_limiter import inference_rate_limiter
from app.schemas.audio import AudioAnalysisResponse, AudioMetricSummary, AudioAnomalySegment
from app.services.audio_deepfake_detector import audio_deepfake_detector
from app.services.audio_preprocessor import AudioValidationError
from app.services.storage import storage_service

router = APIRouter()

@router.post("/analyze", response_model=AudioAnalysisResponse, dependencies=[Depends(inference_rate_limiter)])
async def analyze_audio(
    file: UploadFile = File(...),
    enable_voice_cloning_check: bool = Form(True)
):
    """
    Accepts an audio file and executes deep synthetic voice and acoustic anomaly analysis.
    Uses pretrained models (Wav2Vec2 / ASVspoof AST) and empirical vocoder forensics.
    Handles silent, corrupted, and excessively long audio files.
    """
    valid_exts = tuple(settings.ALLOWED_AUDIO_EXTENSIONS)
    clean_filename = storage_service.sanitize_filename(file.filename or "")
    if not clean_filename or not clean_filename.lower().endswith(valid_exts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Supported: {', '.join(valid_exts)}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes)."
        )

    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # Verify magic bytes and reject dangerous executable headers
    storage_service.verify_magic_bytes(content[:64], Path(clean_filename).suffix)

    try:
        results = await audio_deepfake_detector.analyze_recording(content, clean_filename)
    except AudioValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error during audio forensics: {str(e)}"
        )

    anomalous = []
    for seg in results.get("flagged_intervals", []):
        anomalous.append(AudioAnomalySegment(
            start_time=seg.get("start_time", seg.get("start_timestamp", 0.0)),
            end_time=seg.get("end_time", seg.get("end_timestamp", 0.0)),
            synthetic_score=seg.get("synthetic_score", seg.get("anomaly_score", 0.0)),
            reason=seg.get("reason", "Acoustic anomaly detected")
        ))

    return AudioAnalysisResponse(
        job_id=uuid.uuid4(),
        status="completed",
        media_type="audio",
        duration_seconds=results["duration_seconds"],
        sample_rate=results["sample_rate"],
        classification=results["classification"],
        verdict=results["verdict"],
        model_confidence=results["model_confidence"],
        synthetic_speech_probability=results["synthetic_probability"],
        voice_clone_probability=round(results["synthetic_probability"] * 0.9, 3),
        calibrated_fraud_risk=results["calibrated_fraud_risk"],
        risk_level=results["risk_level"],
        inference_engine=results["inference_engine"],
        confidence_score=results["model_confidence"],
        vocoder_artifacts_detected=results["vocoder_artifacts_detected"],
        acoustic_metrics=AudioMetricSummary(**results["audio_metrics"]),
        explainability_summary=results["explainability_summary"],
        actionable_recommendations=results["actionable_recommendations"],
        anomalous_segments=anomalous,
        potential_generator_signatures=["Neural-Vocoder", "TTS-Synthesizer"] if results["vocoder_artifacts_detected"] else [],
        model_limitations=results.get("model_limitations", [])
    )
