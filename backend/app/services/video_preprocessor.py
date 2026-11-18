"""
Video Preprocessing and Keyframe Extraction Service.
Validates video streams, extracts uniform keyframes across time,
localizes facial bounding boxes, and prepares normalized crops for AI inference.
"""

import os
import io
import cv2
import tempfile
import numpy as np
from PIL import Image, ImageSequence
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass

class VideoValidationError(Exception):
    """Raised when an uploaded video is corrupted, empty, or unparseable."""
    pass

@dataclass
class ExtractedFrame:
    frame_index: int
    timestamp_sec: float
    frame_rgb: np.ndarray
    face_detected: bool
    face_bbox: Optional[Tuple[int, int, int, int]]  # (x, y, w, h) in pixels
    normalized_bbox: Optional[Dict[str, float]]     # {x, y, w, h} in [0.0, 1.0]
    face_crop_rgb: Optional[np.ndarray]            # Normalized (224, 224, 3)

class VideoPreprocessor:
    def __init__(self, target_crop_size: Tuple[int, int] = (224, 224)):
        self.target_crop_size = target_crop_size
        # YCrCb skin chrominance threshold bounds
        self.skin_lower = np.array([0, 133, 77], dtype=np.uint8)
        self.skin_upper = np.array([255, 173, 127], dtype=np.uint8)

    def detect_face(self, frame_bgr: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int, int, int]], Optional[Dict[str, float]], Optional[np.ndarray]]:
        """
        Detects facial region using skin chrominance segmentation and morphological analysis.
        Returns (face_detected, pixel_bbox, normalized_bbox, face_crop_rgb).
        """
        h_img, w_img = frame_bgr.shape[:2]
        if h_img < 30 or w_img < 30:
            return False, None, None, None

        # Convert to YCrCb for illumination-invariant skin chromaticity analysis
        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, self.skin_lower, self.skin_upper)

        # Morphological filtering to eliminate noise and bridge facial cavities
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return False, None, None, None

        total_pixels = h_img * w_img
        valid_candidates = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Face candidate must occupy between 1.5% and 60% of total frame area
            if area < (total_pixels * 0.015) or area > (total_pixels * 0.60):
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / float(h)
            # Human face bounding box aspect ratio is typically between 0.55 and 1.35
            if 0.50 <= aspect_ratio <= 1.40:
                valid_candidates.append((area, (x, y, w, h)))

        if not valid_candidates:
            return False, None, None, None

        # Select largest candidate by contour area
        valid_candidates.sort(key=lambda item: item[0], reverse=True)
        _, (x, y, w, h) = valid_candidates[0]

        # Apply 15% margin around face to include transition boundary seams (jawline, hairline)
        margin_x = int(w * 0.15)
        margin_y = int(h * 0.15)
        pad_x1 = max(0, x - margin_x)
        pad_y1 = max(0, y - margin_y)
        pad_x2 = min(w_img, x + w + margin_x)
        pad_y2 = min(h_img, y + h + margin_y)

        face_w = pad_x2 - pad_x1
        face_h = pad_y2 - pad_y1

        if face_w < 20 or face_h < 20:
            return False, None, None, None

        crop_bgr = frame_bgr[pad_y1:pad_y2, pad_x1:pad_x2]
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        crop_resized = cv2.resize(crop_rgb, self.target_crop_size, interpolation=cv2.INTER_AREA)

        pixel_bbox = (pad_x1, pad_y1, face_w, face_h)
        normalized_bbox = {
            "x": round(float(pad_x1) / float(w_img), 4),
            "y": round(float(pad_y1) / float(h_img), 4),
            "w": round(float(face_w) / float(w_img), 4),
            "h": round(float(face_h) / float(h_img), 4),
        }

        return True, pixel_bbox, normalized_bbox, crop_resized

    def _extract_from_image_sequence(
        self,
        source: Union[str, bytes],
        max_frames: int = 30,
        sample_fps: float = 3.0
    ) -> Tuple[Dict[str, Any], List[ExtractedFrame]]:
        """
        Extracts frames from visual images or animated formats (e.g. WebP, JPG, PNG, GIF).
        """
        try:
            if isinstance(source, bytes):
                im = Image.open(io.BytesIO(source))
            else:
                im = Image.open(source)

            pil_frames = []
            for frame in ImageSequence.Iterator(im):
                pil_frames.append(frame.convert("RGB"))
        except Exception as e:
            raise VideoValidationError(f"Failed to decode image stream: {str(e)}")

        if not pil_frames:
            raise VideoValidationError("Visual media contains no readable frames.")

        total_frames = len(pil_frames)
        frame_durations = [f.info.get("duration", 100) for f in pil_frames]
        total_duration_ms = sum(frame_durations)
        if total_duration_ms <= 0:
            total_duration_ms = total_frames * 1000

        duration_seconds = round(float(total_duration_ms) / 1000.0, 2)
        if duration_seconds <= 0:
            duration_seconds = 1.0

        fps = round(float(total_frames) / duration_seconds, 2) if duration_seconds > 0 else 1.0
        first_frame = pil_frames[0]
        width, height = first_frame.size

        metadata = {
            "duration_seconds": duration_seconds,
            "fps": fps if fps > 0 else 1.0,
            "total_frames": total_frames,
            "resolution": f"{width}x{height}",
            "width": width,
            "height": height,
        }

        # Subsample frames if necessary
        if total_frames > max_frames:
            selected_indices = [int(i) for i in np.linspace(0, total_frames - 1, max_frames, dtype=int)]
        else:
            selected_indices = list(range(total_frames))

        extracted_frames: List[ExtractedFrame] = []
        for idx in selected_indices:
            p_frame = pil_frames[idx]
            frame_rgb = np.array(p_frame)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            timestamp_sec = round(float(idx) / max(fps, 0.1), 2)
            detected, pixel_bbox, norm_bbox, face_crop = self.detect_face(frame_bgr)

            extracted_frames.append(ExtractedFrame(
                frame_index=idx,
                timestamp_sec=timestamp_sec,
                frame_rgb=frame_rgb,
                face_detected=detected,
                face_bbox=pixel_bbox,
                normalized_bbox=norm_bbox,
                face_crop_rgb=face_crop,
            ))

        return metadata, extracted_frames

    def extract_keyframes(
        self,
        video_input: Union[str, bytes],
        max_frames: int = 30,
        sample_fps: float = 3.0
    ) -> Tuple[Dict[str, Any], List[ExtractedFrame]]:
        """
        Parses media container, extracts metadata, and samples keyframes across the timeline.
        video_input: file path or raw bytes buffer.
        """
        # 1. Fast path for images & animated visual formats (WebP, JPG, JPEG, PNG)
        is_image = False
        if isinstance(video_input, bytes):
            if len(video_input) == 0:
                raise VideoValidationError("Uploaded media payload is empty (0 bytes).")
            if (len(video_input) >= 12 and video_input.startswith(b"RIFF") and b"WEBP" in video_input[:16]) or \
               video_input.startswith(b"\xff\xd8\xff") or \
               video_input.startswith(b"\x89PNG\r\n\x1a\n"):
                is_image = True
        elif isinstance(video_input, str):
            if not os.path.exists(video_input):
                raise VideoValidationError(f"Media file does not exist: {video_input}")
            if video_input.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
                is_image = True

        if is_image:
            return self._extract_from_image_sequence(video_input, max_frames=max_frames, sample_fps=sample_fps)

        # 2. General video extraction using OpenCV
        temp_path = None
        if isinstance(video_input, bytes):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
                tf.write(video_input)
                temp_path = tf.name
            target_path = temp_path
        else:
            target_path = video_input

        cap = None
        try:
            cap = cv2.VideoCapture(target_path)
            if not cap.isOpened():
                # Attempt image sequence fallback before throwing
                try:
                    return self._extract_from_image_sequence(target_path, max_frames=max_frames, sample_fps=sample_fps)
                except Exception:
                    raise VideoValidationError("Failed to open video container. Corrupted or unsupported codec.")

            raw_fps = cap.get(cv2.CAP_PROP_FPS)
            fps = float(raw_fps) if raw_fps and raw_fps > 0 else 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if total_frames <= 0 or width <= 0 or height <= 0:
                # Attempt to count frames sequentially if container metadata is incomplete
                frame_count = 0
                while True:
                    ret, _ = cap.read()
                    if not ret:
                        break
                    frame_count += 1
                total_frames = frame_count
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            if total_frames <= 0:
                # Attempt image sequence fallback
                try:
                    return self._extract_from_image_sequence(target_path, max_frames=max_frames, sample_fps=sample_fps)
                except Exception:
                    raise VideoValidationError("Video contains no readable image frames.")

            duration_seconds = round(float(total_frames) / fps, 2)
            resolution = f"{width}x{height}"

            metadata = {
                "duration_seconds": duration_seconds,
                "fps": round(fps, 2),
                "total_frames": total_frames,
                "resolution": resolution,
                "width": width,
                "height": height,
            }

            # Calculate frame sampling step
            step = max(1, int(fps / sample_fps)) if sample_fps > 0 else 1
            sample_indices = list(range(0, total_frames, step))

            # Limit to max_frames evenly distributed
            if len(sample_indices) > max_frames:
                sample_indices = [sample_indices[i] for i in np.linspace(0, len(sample_indices) - 1, max_frames, dtype=int)]

            extracted_frames: List[ExtractedFrame] = []

            for frame_idx in sample_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    continue

                timestamp_sec = round(float(frame_idx) / fps, 2)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                detected, pixel_bbox, norm_bbox, face_crop = self.detect_face(frame_bgr)

                extracted_frames.append(ExtractedFrame(
                    frame_index=frame_idx,
                    timestamp_sec=timestamp_sec,
                    frame_rgb=frame_rgb,
                    face_detected=detected,
                    face_bbox=pixel_bbox,
                    normalized_bbox=norm_bbox,
                    face_crop_rgb=face_crop,
                ))

            if cap is not None:
                cap.release()

            if not extracted_frames:
                # Try image sequence fallback if video keyframe loop extracted 0 frames
                try:
                    return self._extract_from_image_sequence(target_path, max_frames=max_frames, sample_fps=sample_fps)
                except Exception:
                    raise VideoValidationError("Failed to extract any readable keyframes from video stream.")

            return metadata, extracted_frames

        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

video_preprocessor = VideoPreprocessor()

