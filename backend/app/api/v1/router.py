from fastapi import APIRouter
from app.api.v1 import auth, scans, alerts, analytics, audit, audio, video, multimodal, stream, huggingface, retention

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & User Management"])
api_router.include_router(scans.router, prefix="/scans", tags=["Media Scans & Forensic Storage"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Threat Alerts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Cybersecurity Analytics"])
api_router.include_router(audit.router, prefix="/audit", tags=["Forensic Audit Logs"])
api_router.include_router(huggingface.router, prefix="/huggingface", tags=["Hugging Face Dataset Intelligence"])
api_router.include_router(retention.router, prefix="/retention", tags=["Data Retention & Lifecycle Governance"])

# Modular Direct Pipeline Routes
api_router.include_router(audio.router, prefix="/audio", tags=["Audio Forensics"])
api_router.include_router(video.router, prefix="/video", tags=["Video Forensics"])
api_router.include_router(multimodal.router, prefix="/multimodal", tags=["Multimodal Fusion"])
api_router.include_router(stream.router, prefix="/stream", tags=["Real-Time Stream"])
