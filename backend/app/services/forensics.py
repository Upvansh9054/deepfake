import numpy as np
from typing import Dict, Any, Tuple, Optional
from app.ml.video_detector import VideoDetector
from app.ml.multimodal_fusion import MultimodalRiskEngine
from app.services.audio_deepfake_detector import audio_deepfake_detector
from app.services.video_deepfake_detector import video_deepfake_detector
from app.services.multimodal_service import multimodal_service

video_detector = VideoDetector()
fusion_engine = MultimodalRiskEngine()

async def run_media_forensic_pipeline_async(
    file_path: str,
    media_type: str,
    audio_path: Optional[str] = None,
    media_title: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Asynchronous forensic pipeline executing actual AI audio, video,
    and multimodal deepfake detection.
    """
    if media_type == "audio":
        with open(file_path, "rb") as f:
            content = f.read()

        detection = await audio_deepfake_detector.analyze_recording(content, file_path)

        results = {
            "synthetic_prob": detection["synthetic_probability"],
            "spatial_prob": 0.0,
            "temporal_prob": 0.0,
            "audio_metrics": detection["audio_metrics"],
            "video_metrics": {
                "inference_engine": detection["inference_engine"],
                "model_confidence": detection["model_confidence"],
                "classification": detection["classification"],
            },
            "verdict": detection["verdict"],
            "confidence_score": detection["model_confidence"],
            "flagged_intervals": detection["flagged_intervals"],
        }

        report = {
            "composite_risk_score": detection["calibrated_fraud_risk"],
            "risk_level": detection["risk_level"],
            "summary_explanation": detection["explainability_summary"],
            "recommendations": detection["actionable_recommendations"],
            "breakdown": {
                "audio_synthetic_prob": detection["synthetic_probability"],
                "calibrated_fraud_risk": detection["calibrated_fraud_risk"],
                "inference_engine": detection["inference_engine"],
                "vocoder_artifacts_detected": detection["vocoder_artifacts_detected"],
                "model_limitations": detection.get("model_limitations", []),
            },
        }
        return results, report

    elif media_type == "multimodal":
        fused = await multimodal_service.analyze_multimodal(
            video_input=file_path,
            audio_input=audio_path or file_path,
            media_title=media_title
        )

        results = {
            "synthetic_prob": fused["breakdown"]["audio_risk"],
            "spatial_prob": fused["breakdown"]["video_risk"],
            "temporal_prob": fused["breakdown"]["cross_modal_inconsistency"],
            "audio_metrics": fused.get("audio_metrics", {}),
            "video_metrics": {
                "inference_engine": "Multimodal Bayesian Risk Engine",
                "risk_category": fused["risk_category"],
                "evidence_status": fused["breakdown"]["evidence_status"],
                "faces_detected": fused.get("faces_detected", 0),
                "sync_metrics": fused.get("sync_metrics"),
                "signal_attribution": fused["breakdown"]["signal_attribution"],
                "suspicious_timestamps": fused["suspicious_timestamps"],
                "average_blink_rate_per_min": fused.get("video_metrics", {}).get("average_blink_rate_per_min", 15.0),
                "spectral_fft_residual": fused.get("video_metrics", {}).get("spectral_fft_residual", 0.08),
                "boundary_warping_detected": fused.get("video_metrics", {}).get("boundary_warping_detected", False),
            },
            "verdict": fused["verdict"],
            "confidence_score": fused["confidence_score"],
            "flagged_intervals": fused["timeline_anomalies"],
        }

        report = {
            "composite_risk_score": fused["composite_risk_score"],
            "risk_level": "CRITICAL" if fused["composite_risk_score"] > 80 else ("HIGH" if fused["composite_risk_score"] >= 65 else ("MODERATE" if fused["composite_risk_score"] >= 35 else "LOW")),
            "summary_explanation": fused["summary_explanation"],
            "recommendations": fused["actionable_recommendations"],
            "breakdown": {
                "audio_risk": fused["breakdown"]["audio_risk"],
                "video_risk": fused["breakdown"]["video_risk"],
                "sync_error_score": fused["breakdown"]["sync_error_score"],
                "cross_modal_inconsistency": fused["breakdown"]["cross_modal_inconsistency"],
                "evidence_status": fused["breakdown"]["evidence_status"],
                "signal_attribution": fused["breakdown"]["signal_attribution"],
                "risk_category": fused["risk_category"],
                "faces_detected": fused.get("faces_detected", 0),
                "suspicious_timestamps": fused["suspicious_timestamps"],
                "model_limitations": fused["model_limitations"],
            },
        }
        return results, report

    else:  # video
        # Check if video file has audio stream for multimodal deepfake fusion
        has_audio = False
        try:
            import subprocess, imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            proc = subprocess.run([ffmpeg_exe, "-i", file_path], capture_output=True, text=True, errors="ignore")
            has_audio = "Audio:" in proc.stderr
        except Exception:
            has_audio = False

        if has_audio:
            fused = await multimodal_service.analyze_multimodal(
                video_input=file_path,
                audio_input=file_path,
                media_title=media_title
            )

            results = {
                "synthetic_prob": fused["breakdown"]["audio_risk"],
                "spatial_prob": fused["breakdown"]["video_risk"],
                "temporal_prob": fused["breakdown"]["cross_modal_inconsistency"],
                "audio_metrics": {},
                "video_metrics": {
                    "inference_engine": "Multimodal Bayesian Risk Engine",
                    "risk_category": fused["risk_category"],
                    "evidence_status": fused["breakdown"]["evidence_status"],
                    "sync_metrics": fused.get("sync_metrics"),
                    "signal_attribution": fused["breakdown"]["signal_attribution"],
                    "suspicious_timestamps": fused["suspicious_timestamps"],
                },
                "verdict": fused["verdict"],
                "confidence_score": fused["confidence_score"],
                "flagged_intervals": fused["timeline_anomalies"],
            }

            report = {
                "composite_risk_score": fused["composite_risk_score"],
                "risk_level": "CRITICAL" if fused["composite_risk_score"] > 80 else ("HIGH" if fused["composite_risk_score"] >= 65 else ("MODERATE" if fused["composite_risk_score"] >= 35 else "LOW")),
                "summary_explanation": fused["summary_explanation"],
                "recommendations": fused["actionable_recommendations"],
                "breakdown": {
                    "audio_risk": fused["breakdown"]["audio_risk"],
                    "video_risk": fused["breakdown"]["video_risk"],
                    "sync_error_score": fused["breakdown"]["sync_error_score"],
                    "cross_modal_inconsistency": fused["breakdown"]["cross_modal_inconsistency"],
                    "evidence_status": fused["breakdown"]["evidence_status"],
                    "signal_attribution": fused["breakdown"]["signal_attribution"],
                    "risk_category": fused["risk_category"],
                    "suspicious_timestamps": fused["suspicious_timestamps"],
                    "model_limitations": fused["model_limitations"],
                },
            }
            return results, report

        try:
            video_res = await video_deepfake_detector.analyze_video(file_path, max_frames=30, sample_fps=3.0)
        except Exception as e:
            video_res = {
                "spatial_manipulation_score": 0.0,
                "temporal_inconsistency_score": 0.0,
                "verdict": "inconclusive",
                "model_confidence": 0.0,
                "classification": "uncertain",
                "calibrated_fraud_risk": 0.0,
                "risk_level": "LOW",
                "inference_engine": "Video Forensic Container Decoder",
                "total_frames_sampled": 0,
                "faces_detected": 0,
                "suspicious_timestamps": [],
                "flagged_intervals": [],
                "video_metrics": {
                    "faces_detected": 0,
                    "eye_blinking_anomaly": False,
                    "average_blink_rate_per_min": 0.0,
                    "boundary_warping_detected": False,
                    "landmark_jitter_score": 0.0,
                    "spectral_fft_residual": 0.0,
                    "facial_boundary_disparity": 0.0,
                },
                "explainability_summary": f"Video inspection could not decode container frames: {str(e)}",
                "actionable_recommendations": [
                    "Verify file integrity and re-encode using standard H.264/MP4 container settings."
                ],
                "model_limitations": [
                    "Corrupted, truncated, or non-standard video streams cannot be parsed."
                ],
            }

        p_spatial = video_res["spatial_manipulation_score"]
        p_temporal = video_res["temporal_inconsistency_score"]
        verdict = video_res["verdict"]
        confidence = video_res["model_confidence"]
        composite_risk = video_res["calibrated_fraud_risk"]
        risk_level = video_res["risk_level"]

        # Merge video metrics with metadata for comprehensive storage
        v_metrics = dict(video_res["video_metrics"])
        v_metrics.update({
            "inference_engine": video_res["inference_engine"],
            "model_confidence": video_res["model_confidence"],
            "classification": video_res["classification"],
            "total_frames_sampled": video_res["total_frames_sampled"],
            "suspicious_timestamps": video_res["suspicious_timestamps"],
        })

        results = {
            "synthetic_prob": 0.0,
            "spatial_prob": p_spatial,
            "temporal_prob": p_temporal,
            "audio_metrics": {},
            "video_metrics": v_metrics,
            "verdict": verdict,
            "confidence_score": confidence,
            "flagged_intervals": video_res["flagged_intervals"],
        }

        report = {
            "composite_risk_score": composite_risk,
            "risk_level": risk_level,
            "summary_explanation": video_res["explainability_summary"],
            "recommendations": video_res["actionable_recommendations"],
            "breakdown": {
                "spatial_manipulation_score": p_spatial,
                "temporal_inconsistency_score": p_temporal,
                "calibrated_fraud_risk": composite_risk,
                "classification": video_res["classification"],
                "inference_engine": video_res["inference_engine"],
                "faces_detected": video_res["faces_detected"],
                "total_frames_sampled": video_res["total_frames_sampled"],
                "suspicious_timestamps": video_res["suspicious_timestamps"],
                "model_limitations": video_res.get("model_limitations", []),
            },
        }
        return results, report

def run_media_forensic_pipeline(file_path: str, media_type: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Synchronous wrapper for backward compatibility."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_media_forensic_pipeline_async(file_path, media_type))
                return future.result()
        else:
            return loop.run_until_complete(run_media_forensic_pipeline_async(file_path, media_type))
    except Exception:
        return asyncio.run(run_media_forensic_pipeline_async(file_path, media_type))
