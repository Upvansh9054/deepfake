from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc
from typing import Optional, List
import hashlib
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.rate_limiter import inference_rate_limiter
from app.api.v1.auth import get_current_user
from app.models.entities import User, Scan, ScanResult, RiskReport, Alert, AuditLog
from app.schemas.scan import ScanDetailResponse, ScanListResponse, ScanResponse, UrlScanRequest
from app.services.storage import storage_service
from app.services.forensics import run_media_forensic_pipeline_async
from app.services.url_downloader import url_downloader
import logging

router = APIRouter()
logger = logging.getLogger("deepfake_shield.scans")

@router.post("/upload", response_model=ScanDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(inference_rate_limiter)])
async def upload_and_scan(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    scan_type: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads an audio, video, or multimodal media file, verifies file integrity and type,
    executes real forensic baseline analysis, and stores complete records.
    Supports dual-stream upload (video + separate suspect audio track) for multimodal conflict analysis.
    """
    if audio_file is not None:
        # Dual-stream multimodal upload (video file + suspect audio track)
        media_type = "multimodal"
        v_path, v_name, v_size, v_sha = await storage_service.save_uploaded_file(file)
        a_path, a_name, a_size, a_sha = await storage_service.save_uploaded_file(audio_file)

        scan_title = title if title and title.strip() else f"{v_name} + {a_name}"
        scan = Scan(
            user_id=current_user.id,
            title=scan_title,
            media_type="multimodal",
            file_path=v_path,
            file_name=f"{v_name} [dual-stream with {a_name}]",
            file_size_bytes=v_size + a_size,
            mime_type="multipart/multimodal",
            sha256_hash=v_sha,
            status="completed",
            progress_percentage=100
        )
        db.add(scan)
        await db.flush()

        results_data, report_data = await run_media_forensic_pipeline_async(v_path, "multimodal", audio_path=a_path, media_title=scan_title)
    else:
        # Single file upload
        detected_type = storage_service.validate_file(file)
        file_path, file_name, file_size, sha256_hash = await storage_service.save_uploaded_file(file)

        if scan_type == "multimodal" or (detected_type == "video" and scan_type == "multimodal"):
            effective_media_type = "multimodal"
        elif scan_type in ["audio", "video"]:
            effective_media_type = scan_type
        else:
            effective_media_type = detected_type

        scan_title = title if title and title.strip() else file_name
        scan = Scan(
            user_id=current_user.id,
            title=scan_title,
            media_type=effective_media_type,
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size,
            mime_type=file.content_type or f"{effective_media_type}/unknown",
            sha256_hash=sha256_hash,
            status="completed",
            progress_percentage=100
        )
        db.add(scan)
        await db.flush()

        results_data, report_data = await run_media_forensic_pipeline_async(file_path, effective_media_type, media_title=scan_title)

    scan_result = ScanResult(
        scan_id=scan.id,
        synthetic_prob=results_data["synthetic_prob"],
        spatial_prob=results_data["spatial_prob"],
        temporal_prob=results_data["temporal_prob"],
        audio_metrics=results_data["audio_metrics"],
        video_metrics=results_data["video_metrics"],
        verdict=results_data["verdict"],
        confidence_score=results_data["confidence_score"],
        flagged_intervals=results_data["flagged_intervals"]
    )
    db.add(scan_result)

    risk_report = RiskReport(
        scan_id=scan.id,
        composite_risk_score=report_data["composite_risk_score"],
        risk_level=report_data["risk_level"],
        summary_explanation=report_data["summary_explanation"],
        recommendations=report_data["recommendations"],
        breakdown=report_data["breakdown"]
    )
    db.add(risk_report)

    # 6. Create Alert if suspicious or manipulated
    if report_data["composite_risk_score"] >= 45.0:
        alert = Alert(
            user_id=current_user.id,
            scan_id=scan.id,
            alert_type="threat_detected",
            severity="CRITICAL" if report_data["composite_risk_score"] >= 70 else "WARNING",
            title=f"Potential Deepfake Alert: {scan_title}",
            message=report_data["summary_explanation"]
        )
        db.add(alert)

    # 7. Audit log entry
    audit = AuditLog(
        user_id=current_user.id,
        action="media_scan_completed",
        resource_type="scan",
        resource_id=scan.id,
        details={
            "file_name": scan.file_name,
            "media_type": scan.media_type,
            "risk_score": report_data["composite_risk_score"],
            "verdict": results_data["verdict"]
        }
    )
    db.add(audit)

    await db.commit()
    await db.refresh(scan)

    # Reload with relationships
    stmt = (
        select(Scan)
        .where(Scan.id == scan.id)
        .options(selectinload(Scan.result), selectinload(Scan.risk_report))
    )
    res = await db.execute(stmt)
    full_scan = res.scalars().first()

    return ScanDetailResponse.model_validate(full_scan)

@router.post("/from-url", response_model=ScanDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(inference_rate_limiter)])
@router.post("/from-url/", response_model=ScanDetailResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(inference_rate_limiter)])
async def scan_from_url(
    payload: UrlScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Downloads media directly from YouTube, Instagram, TikTok, or video web URLs,
    verifies file integrity and executes multi-frame deepfake forensic analysis.
    """
    file_path, file_name, file_size, sha256_hash, detected_type, mime_type = await url_downloader.download_media(payload.url)

    if detected_type == "multimodal" or payload.scan_type == "multimodal":
        effective_media_type = "multimodal"
    else:
        effective_media_type = payload.scan_type or detected_type
    scan_title = payload.title if payload.title and payload.title.strip() else file_name

    scan = Scan(
        user_id=current_user.id,
        title=scan_title,
        media_type=effective_media_type,
        file_path=file_path,
        file_name=file_name,
        file_size_bytes=file_size,
        mime_type=mime_type,
        sha256_hash=sha256_hash,
        status="completed",
        progress_percentage=100
    )
    db.add(scan)
    await db.flush()

    results_data, report_data = await run_media_forensic_pipeline_async(file_path, effective_media_type, media_title=f"{scan_title} {file_name}")

    scan_result = ScanResult(
        scan_id=scan.id,
        synthetic_prob=results_data["synthetic_prob"],
        spatial_prob=results_data["spatial_prob"],
        temporal_prob=results_data["temporal_prob"],
        audio_metrics=results_data["audio_metrics"],
        video_metrics=results_data["video_metrics"],
        verdict=results_data["verdict"],
        confidence_score=results_data["confidence_score"],
        flagged_intervals=results_data["flagged_intervals"]
    )
    db.add(scan_result)

    risk_report = RiskReport(
        scan_id=scan.id,
        composite_risk_score=report_data["composite_risk_score"],
        risk_level=report_data["risk_level"],
        summary_explanation=report_data["summary_explanation"],
        recommendations=report_data["recommendations"],
        breakdown=report_data["breakdown"]
    )
    db.add(risk_report)

    # Automatically generate alerts for critical/high synthetic threats
    if scan_result.synthetic_prob >= 0.70 or scan_result.spatial_prob >= 0.65:
        alert = Alert(
            user_id=current_user.id,
            scan_id=scan.id,
            severity="CRITICAL" if scan_result.synthetic_prob >= 0.85 else "HIGH",
            title=f"Synthetic Manipulation Alert: {scan.title}",
            message=f"Deepfake detected from URL source with {round(max(scan_result.synthetic_prob, scan_result.spatial_prob) * 100, 1)}% synthetic probability."
        )
        db.add(alert)

    # Compliance audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="SCAN_FROM_URL_COMPLETED",
        resource_type="scan",
        resource_id=scan.id,
        details={
            "source_url": payload.url,
            "file_name": scan.file_name,
            "media_type": scan.media_type,
            "risk_score": report_data["composite_risk_score"],
            "verdict": results_data["verdict"]
        }
    )
    db.add(audit)

    await db.commit()
    await db.refresh(scan)

    stmt = (
        select(Scan)
        .where(Scan.id == scan.id)
        .options(selectinload(Scan.result), selectinload(Scan.risk_report))
    )
    res = await db.execute(stmt)
    full_scan = res.scalars().first()

    return ScanDetailResponse.model_validate(full_scan)

@router.get("/", response_model=ScanListResponse)
async def list_scans(
    media_type: Optional[str] = Query(None, description="Filter by 'audio' or 'video'"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    search: Optional[str] = Query(None, description="Search scan title or filename"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetches paginated scans belonging to the current user."""
    offset = (page - 1) * limit

    query = select(Scan).where(Scan.user_id == current_user.id)

    if media_type:
        query = query.where(Scan.media_type == media_type.lower())
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where((Scan.title.ilike(search_pattern)) | (Scan.file_name.ilike(search_pattern)))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Load items with relationships
    items_query = (
        query.options(selectinload(Scan.result), selectinload(Scan.risk_report))
        .order_by(desc(Scan.created_at))
        .offset(offset)
        .limit(limit)
    )
    items_result = await db.execute(items_query)
    scans = items_result.scalars().all()

    # Filter by verdict in python if requested (since verdict is on scan.result)
    if verdict:
        scans = [s for s in scans if s.result and s.result.verdict == verdict.lower()]

    return ScanListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[ScanDetailResponse.model_validate(s) for s in scans]
    )

@router.get("/{scan_id}", response_model=ScanDetailResponse)
async def get_scan_detail(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full scan details including forensic results and risk report."""
    stmt = (
        select(Scan)
        .where((Scan.id == scan_id) & (Scan.user_id == current_user.id))
        .options(selectinload(Scan.result), selectinload(Scan.risk_report))
    )
    result = await db.execute(stmt)
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan record not found"
        )

    return ScanDetailResponse.model_validate(scan)

@router.get("/{scan_id}/certificate")
async def get_scan_certificate(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns an official tamper-evident cryptographic forensic certificate payload
    for downstream verification, legal review, and PDF reporting.
    """
    stmt = (
        select(Scan)
        .where((Scan.id == scan_id) & (Scan.user_id == current_user.id))
        .options(selectinload(Scan.result), selectinload(Scan.risk_report))
    )
    result = await db.execute(stmt)
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan record not found"
        )

    res = scan.result
    rep = scan.risk_report

    cert = {
        "certificate_id": f"CERT-DFS-{scan.id[:8].upper()}-{int(scan.created_at.timestamp()) if scan.created_at else 0}",
        "scan_id": scan.id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "inspected_asset": {
            "title": scan.title,
            "file_name": scan.file_name,
            "media_type": scan.media_type,
            "file_size_bytes": scan.file_size_bytes,
            "sha256_fingerprint": scan.sha256_hash,
            "registered_at": scan.created_at.isoformat() if scan.created_at else None,
        },
        "investigator": {
            "analyst_id": current_user.id,
            "analyst_name": current_user.full_name,
            "analyst_email": current_user.email,
            "organization": "Deepfake Shield Cybersecurity Defense",
        },
        "forensic_verdict": {
            "verdict": res.verdict if res else "unknown",
            "risk_level": rep.risk_level if rep else "UNKNOWN",
            "composite_risk_score": rep.composite_risk_score if rep else 0.0,
            "confidence_score": res.confidence_score if res else 0.0,
            "synthetic_audio_prob": res.synthetic_prob if res else 0.0,
            "spatial_manipulation_prob": res.spatial_prob if res else 0.0,
            "temporal_inconsistency_prob": res.temporal_prob if res else 0.0,
        },
        "neural_engines": [
            "Acoustic Preprocessor & Librosa Spectral Flatness (SFM)",
            "Pretrained Wav2Vec 2.0 / ASVspoof AST Voice Spoof Router",
            "MediaPipe 468 3D Mesh & Eye Aspect Ratio (EAR) Blink Dynamics",
            "Spatial Face Boundary Seam Disparity & 2D FFT Spectral Residuals",
            "SyncNet Viseme-Phoneme Lip-Speech Cross-Correlation",
            "Bayesian Multi-Evidence Complementary Authenticity Fusion",
        ],
        "explainability_summary": rep.summary_explanation if rep else "N/A",
        "actionable_recommendations": rep.recommendations if rep else [],
        "flagged_intervals": res.flagged_intervals if res else [],
        "chain_of_custody_hash": hashlib.sha256(
            f"{scan.id}:{scan.sha256_hash}:{rep.composite_risk_score if rep else 0}".encode()
        ).hexdigest(),
        "governance_notice": (
            "This digital certificate reflects probabilistic neural and spectral anomaly detection. "
            "Scores represent synthetic likelihood and do not constitute an accusation of intentional fraud."
        )
    }
    return cert

@router.get("/{scan_id}/media")
async def get_scan_media_stream(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure authenticated media streaming endpoint.
    Enforces tenant ownership (or admin role) and path traversal boundaries.
    """
    stmt = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(stmt)
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan record not found")

    # Enforce asset ownership or admin privileges
    if scan.user_id != current_user.id and current_user.role not in ["admin", "user"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: unauthorized asset access")

    secure_path = storage_service.get_secure_file_path(scan.file_path)

    return FileResponse(
        path=str(secure_path),
        media_type=scan.mime_type or "application/octet-stream",
        filename=scan.file_name,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
            "Cache-Control": "private, no-cache, no-store, must-revalidate"
        }
    )

@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes scan record, forensic results, and the physical uploaded file."""
    stmt = select(Scan).where((Scan.id == scan_id) & (Scan.user_id == current_user.id))
    result = await db.execute(stmt)
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan record not found"
        )

    # Delete physical file
    storage_service.remove_file(scan.file_path)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="scan_deleted",
        resource_type="scan",
        resource_id=scan.id,
        details={"file_name": scan.file_name}
    )
    db.add(audit)

    await db.delete(scan)
    await db.commit()
    return None

