import os
import re
import hashlib
import uuid
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger("deepfake_shield.storage")

# Common dangerous binary headers
DANGEROUS_MAGIC_HEADERS = [
    (b"MZ", "Windows PE Executable / DLL"),
    (b"\x7fELF", "Linux ELF Executable / Binary"),
    (b"\xca\xfe\xba\xbe", "Mach-O / Java Bytecode"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit"),
    (b"#!", "Shell / Bash Script"),
    (b"<?php", "PHP Executable Script"),
    (b"<script", "HTML Script"),
    (b"<html>", "HTML Document"),
]

class StorageService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR.resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def sanitize_filename(self, filename: str) -> str:
        """
        Strips directory components and replaces unsafe characters to prevent path traversal attacks.
        """
        # Take only the basename, strip path separators
        clean_name = Path(filename).name
        # Remove null bytes and non-alphanumeric/period/dash/underscore
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)
        # Prevent hidden files starting with .
        if clean_name.startswith('.'):
            clean_name = f"file{clean_name}"
        return clean_name[:100] if clean_name else f"upload_{uuid.uuid4().hex[:8]}"

    def verify_magic_bytes(self, header: bytes, ext: str) -> bool:
        """
        Verifies that file starts with legitimate media container magic bytes
        and does not match known executable / script signatures.
        """
        if len(header) < 4:
            return False

        # 1. Reject outright any executable or script magic headers
        for magic, desc in DANGEROUS_MAGIC_HEADERS:
            if header.startswith(magic):
                logger.warning(f"Malicious file upload attempt detected! Blocked {desc} header.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Security violation: File header matches blocked executable or script format ({desc})."
                )

        ext_clean = ext.lower()

        # 2. Audio signatures
        if ext_clean == ".wav":
            # WAV files start with 'RIFF' and contain 'WAVE' in the initial container header
            if not header.startswith(b"RIFF") or (len(header) >= 12 and b"WAVE" not in header[:64]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid WAV file: Magic header does not match RIFF/WAVE container."
                )
        elif ext_clean == ".mp3":
            # MP3 files usually start with ID3 tag (b"ID3") or sync frame (0xFF 0xFB/F3/F2)
            has_id3 = header.startswith(b"ID3")
            has_sync = (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0)
            if not (has_id3 or has_sync):
                # We allow it with a warning if audio header is non-standard but safe
                logger.debug("MP3 header has no ID3 or standard sync word, proceeding with caution.")
        elif ext_clean == ".flac":
            if not header.startswith(b"fLaC"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid FLAC file: Header must begin with 'fLaC'."
                )
        elif ext_clean == ".ogg":
            if not header.startswith(b"OggS"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OGG file: Header must begin with 'OggS'."
                )

        # 3. Video signatures
        elif ext_clean in [".mp4", ".mov", ".m4a"]:
            # MP4/MOV containers typically have 'ftyp' or 'moov' in bytes 4-12
            if len(header) >= 12 and b"ftyp" not in header[:16] and b"moov" not in header[:16]:
                # Non-standard or fragmented mp4, log warning
                logger.debug(f"Video {ext_clean} container missing standard ftyp box.")
        elif ext_clean in [".webm", ".mkv"]:
            # EBML header: 0x1A 0x45 0xDF 0xA3
            if not header.startswith(b"\x1a\x45\xdf\xa3"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid WebM/MKV file: Header must start with EBML sequence."
                )
        elif ext_clean == ".avi":
            if not header.startswith(b"RIFF") or (len(header) >= 12 and header[8:12] != b"AVI "):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid AVI file: Header does not match RIFF/AVI container."
                )
        elif ext_clean == ".webp":
            if not header.startswith(b"RIFF") or (len(header) >= 12 and b"WEBP" not in header[:16]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid WebP file: Header does not match RIFF/WEBP container."
                )
        elif ext_clean in [".jpg", ".jpeg"]:
            if not header.startswith(b"\xff\xd8\xff"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JPEG file: Header does not match standard JPEG signature."
                )
        elif ext_clean == ".png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PNG file: Header does not match standard PNG signature."
                )

        return True

    def validate_file(self, file: UploadFile, expected_type: str = "any") -> str:
        """
        Validates file extension, size, and category (audio or video).
        Returns detected media_type ('audio' or 'video').
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty"
            )

        clean_filename = self.sanitize_filename(file.filename)
        ext = Path(clean_filename).suffix.lower()

        is_audio = ext in settings.ALLOWED_AUDIO_EXTENSIONS
        is_video = ext in settings.ALLOWED_VIDEO_EXTENSIONS

        if not is_audio and not is_video:
            allowed = settings.ALLOWED_AUDIO_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed)}"
            )

        if expected_type == "audio" and not is_audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected an audio file, but received '{ext}'. Allowed audio: {', '.join(settings.ALLOWED_AUDIO_EXTENSIONS)}"
            )

        if expected_type == "video" and not is_video:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected a video file, but received '{ext}'. Allowed video: {', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)}"
            )

        return "audio" if is_audio else "video"

    async def save_uploaded_file(self, file: UploadFile) -> Tuple[str, str, int, str]:
        """
        Saves file chunk-by-chunk to disk, verifies size limit, computes SHA-256 hash,
        and inspects magic bytes for executable/malicious content.
        Returns (relative_file_path, original_filename, file_size_bytes, sha256_hash).
        """
        raw_filename = file.filename or "uploaded_media.bin"
        clean_filename = self.sanitize_filename(raw_filename)
        ext = Path(clean_filename).suffix.lower()

        unique_prefix = uuid.uuid4().hex[:12]
        unique_filename = f"{unique_prefix}_{Path(clean_filename).stem[:30]}{ext}"
        destination_path = self.upload_dir / unique_filename

        hasher = hashlib.sha256()
        total_size = 0
        first_chunk_checked = False

        try:
            with open(destination_path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    
                    if not first_chunk_checked:
                        # Inspect initial magic bytes
                        self.verify_magic_bytes(chunk[:64], ext)
                        first_chunk_checked = True

                    total_size += len(chunk)
                    if total_size > self.max_bytes:
                        # Clean up partial file
                        buffer.close()
                        if destination_path.exists():
                            destination_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
                        )
                    hasher.update(chunk)
                    buffer.write(chunk)
        except HTTPException:
            if destination_path.exists():
                destination_path.unlink()
            raise
        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to securely save file: {str(e)}"
            )

        if total_size == 0:
            if destination_path.exists():
                destination_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        return str(destination_path), clean_filename, total_size, hasher.hexdigest()

    def get_secure_file_path(self, file_path_str: str) -> Path:
        """
        Resolves path and enforces that the file strictly resides inside upload_dir
        to prevent directory traversal and unauthorized filesystem leakage.
        """
        target = Path(file_path_str).resolve()
        try:
            # Check if target is inside self.upload_dir
            target.relative_to(self.upload_dir)
        except ValueError:
            logger.error(f"Directory traversal attempt detected: {file_path_str}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: target file is outside secure storage boundary."
            )

        if not target.exists() or not target.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical media asset not found on storage."
            )

        return target

    def remove_file(self, file_path: str):
        """Safely removes file from disk if within upload boundary."""
        try:
            p = self.get_secure_file_path(file_path)
            if p.exists() and p.is_file():
                p.unlink()
                logger.info(f"Securely removed stored file: {p.name}")
        except Exception as e:
            logger.warning(f"Could not remove file {file_path}: {e}")

storage_service = StorageService()
