"""
Seeds default demo security analyst and sample scans for instant testing.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.core.database import init_db, AsyncSessionLocal
from app.models.entities import User, Scan, ScanResult, RiskReport, Alert, AuditLog, DatasetMetadata
from app.core.security import get_password_hash
from sqlalchemy.future import select

async def seed_data():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Check if analyst already exists
        res = await session.execute(select(User).where(User.email == "analyst@shield.ai"))
        existing_user = res.scalars().first()

        if not existing_user:
            demo_user = User(
                email="analyst@shield.ai",
                hashed_password=get_password_hash("CyberSecurity2026!"),
                full_name="Alex Mercer (Lead Threat Analyst)",
                role="admin"
            )
            session.add(demo_user)
            await session.flush()

            # Seed demo Audio Scan
            scan_audio = Scan(
                user_id=demo_user.id,
                title="C-Level Voice Wire Fraud Sample",
                media_type="audio",
                file_path="storage/uploads/demo_audio_wire.wav",
                file_name="executive_call_recording.wav",
                file_size_bytes=1048576,
                mime_type="audio/wav",
                sha256_hash="d8e8fca2dc0f896fd7cb4cb0031ba249",
                status="completed",
                progress_percentage=100
            )
            session.add(scan_audio)
            await session.flush()

            session.add(ScanResult(
                scan_id=scan_audio.id,
                synthetic_prob=0.88,
                spatial_prob=0.0,
                temporal_prob=0.0,
                audio_metrics={
                    "spectral_flatness_mean": 0.084,
                    "spectral_centroid_mean": 2420.5,
                    "zero_crossing_rate_mean": 0.12,
                    "high_frequency_energy_ratio": 0.009
                },
                video_metrics={},
                verdict="manipulated",
                confidence_score=0.91,
                flagged_intervals=[{
                    "start_time": 1.2,
                    "end_time": 4.8,
                    "synthetic_score": 0.94,
                    "reason": "HiFi-GAN vocoder phase cutoff and robotic formant synthesis"
                }]
            ))

            session.add(RiskReport(
                scan_id=scan_audio.id,
                composite_risk_score=88.0,
                risk_level="CRITICAL",
                summary_explanation="High-confidence synthetic voice detected. Frequency spectral distribution matches known neural voice conversion vocoders with steep 4kHz cutoff.",
                recommendations=[
                    "Block incoming wire instructions authorized via this audio.",
                    "Require dual out-of-band biometric authentication.",
                    "Preserve audio file hash for law enforcement forensic dossier."
                ],
                breakdown={"audio_synthetic_prob": 0.88, "vocoder_signature": "HiFi-GAN"}
            ))

            # Seed demo Video Scan
            scan_video = Scan(
                user_id=demo_user.id,
                title="Video Conference Face-Swap Intercept",
                media_type="video",
                file_path="storage/uploads/demo_faceswap.mp4",
                file_name="meeting_recorded_feed.mp4",
                file_size_bytes=8388608,
                mime_type="video/mp4",
                sha256_hash="9f83c12a7b6d5e4a3b2c1d0e9f8a7b6c",
                status="completed",
                progress_percentage=100
            )
            session.add(scan_video)
            await session.flush()

            session.add(ScanResult(
                scan_id=scan_video.id,
                synthetic_prob=0.0,
                spatial_prob=0.84,
                temporal_prob=0.72,
                audio_metrics={},
                video_metrics={
                    "faces_detected": 1,
                    "eye_blinking_anomaly": True,
                    "average_blink_rate_per_min": 2.4,
                    "boundary_warping_detected": True,
                    "landmark_jitter_score": 0.72
                },
                verdict="manipulated",
                confidence_score=0.89,
                flagged_intervals=[{
                    "start_sec": 0.0,
                    "end_sec": 5.0,
                    "confidence": 0.89,
                    "manipulation_type": "facial_boundary_gradient_discontinuity",
                    "bounding_box": {"x": 0.25, "y": 0.20, "w": 0.50, "h": 0.60}
                }]
            ))

            session.add(RiskReport(
                scan_id=scan_video.id,
                composite_risk_score=84.0,
                risk_level="CRITICAL",
                summary_explanation="Deepfake face-swap detected with 84% composite risk. Eye blink rate suppressed to 2.4 blinks/min (normal: 14-20) and edge boundary blurring detected.",
                recommendations=[
                    "Quarantine video feed and initiate secondary visual challenge (head turn / hand-to-face).",
                    "Review facial boundary seam under infrared or frequency transform.",
                    "Flag host IP address in security gateway."
                ],
                breakdown={"spatial_boundary_score": 0.84, "temporal_jitter": 0.72}
            ))

            # Seed demo Alert
            session.add(Alert(
                user_id=demo_user.id,
                scan_id=scan_audio.id,
                alert_type="threat_detected",
                severity="CRITICAL",
                title="Critical Threat: Executive Voice Clone Detected",
                message="High-confidence synthetic voice detected on C-Level Voice Wire Fraud Sample."
            ))

            session.add(Alert(
                user_id=demo_user.id,
                scan_id=scan_video.id,
                alert_type="threat_detected",
                severity="WARNING",
                title="Warning: Facial Warping & Blink Suppression Flagged",
                message="Meeting video feed exhibits unnatural blink rate and boundary seam artifacts."
            ))

            # Seed demo Audit Logs
            session.add(AuditLog(
                user_id=demo_user.id,
                action="system_initialized",
                resource_type="system",
                resource_id="init-1",
                details={"version": "2.0.0", "status": "active"}
            ))

        # Check and seed Hugging Face Dataset Metadata cache
        res_ds = await session.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_id == "UniDataPro/deepfake-videos-dataset")
        )
        if not res_ds.scalars().first():
            ds_meta = DatasetMetadata(
                dataset_id="UniDataPro/deepfake-videos-dataset",
                author="UniDataPro",
                description="DeepFake Videos for detection tasks. Dataset features video clips for research in deepfake detection.",
                license="cc-by-nc-nd-4.0",
                tags=["video-classification", "deepfake", "Facial Recognition", "security"],
                splits=[{"dataset": "UniDataPro/deepfake-videos-dataset", "config": "default", "split": "train"}],
                total_rows=10,
                parquet_urls=["https://huggingface.co/api/datasets/UniDataPro/deepfake-videos-dataset/parquet/default/train/0.parquet"],
                features_schema=[
                    {"name": "video", "type": {"_type": "Video"}},
                    {"name": "label", "type": {"_type": "ClassLabel", "names": ["deepfake", "video"]}}
                ]
            )
            session.add(ds_meta)
            print("Hugging Face dataset metadata seeded.")

        await session.commit()
        print("Demo database readiness verified.")

if __name__ == "__main__":
    asyncio.run(seed_data())

