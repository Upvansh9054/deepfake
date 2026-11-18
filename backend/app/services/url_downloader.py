"""
URL Media Downloader Service.
Securely downloads media from YouTube, Instagram, TikTok, and direct video URLs
with SSRF defense, file size enforcement, and cryptographic verification.
"""

import os
import uuid
import ipaddress
import hashlib
import asyncio
import logging
from urllib.parse import urlparse
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.services.storage import storage_service

logger = logging.getLogger("deepfake_shield.url_downloader")

class UrlDownloaderService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        os.makedirs(self.upload_dir, exist_ok=True)

    def validate_url_safety(self, url_str: str) -> None:
        """
        Validates URL syntax and blocks loopback, private RFC-1918 addresses, and SSRF attacks.
        """
        if not url_str or not isinstance(url_str, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid video URL must be provided."
            )

        url_clean = url_str.strip()
        try:
            parsed = urlparse(url_clean)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed URL provided."
            )

        if parsed.scheme.lower() not in ["http", "https"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only HTTP and HTTPS URLs are supported."
            )

        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL is missing a valid domain hostname."
            )

        # Block loopback / localhost
        if hostname.lower() in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requests to localhost or private loopback addresses are prohibited."
            )

        # Check for private IP literals
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Requests to private or internal network IP addresses are forbidden."
                )
        except ValueError:
            # Domain name (e.g. youtube.com, instagram.com)
            pass

    async def download_media(self, url: str) -> Tuple[str, str, int, str, str, str]:
        """
        Downloads video or visual media from a URL using yt-dlp or direct HTTP streaming.
        Returns (relative_file_path, original_title, file_size_bytes, sha256_hash, detected_media_type, mime_type).
        """
        self.validate_url_safety(url)
        url_clean = url.strip()

        # Generate unique file stem
        unique_prefix = uuid.uuid4().hex[:12]

        # 1. Attempt download via yt-dlp (handles YouTube, Instagram, TikTok, etc.)
        try:
            result = await self._download_via_ytdlp(url_clean, unique_prefix)
            if result is not None:
                return result
        except HTTPException:
            raise
        except Exception as e:
            logger.info(f"yt-dlp extraction did not complete for {url_clean} ({str(e)}), attempting direct stream...")

        # If it's a known streaming platform and yt-dlp failed, do not attempt direct HTTP GET (which returns HTML)
        is_known_platform = any(d in url_clean.lower() for d in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com"])
        if is_known_platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to access video stream from this link. Please verify the video is public, accessible, and not age-restricted or removed."
            )

        # 2. Fallback to direct HTTP stream download (e.g. direct mp4, webm, webp, jpg links)
        return await self._download_via_httpx(url_clean, unique_prefix)

    async def _download_via_ytdlp(self, url: str, unique_prefix: str) -> Optional[Tuple[str, str, int, str, str, str]]:
        import yt_dlp
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        # Target template inside upload_dir (using %(id)s to ensure valid filenames on Windows without pipes/illegal chars)
        out_template = str(self.upload_dir / f"{unique_prefix}_%(id)s.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg_exe,
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "max_filesize": self.max_bytes,
            "socket_timeout": 35,
            "restrictfilenames": True,
            "js_runtimes": {"node": {}},
        }

        def _run_extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                # In case yt-dlp merged or changed extension
                if not os.path.exists(downloaded_file):
                    for f in self.upload_dir.iterdir():
                        if f.stem.startswith(unique_prefix):
                            downloaded_file = str(f)
                            break
                return info, downloaded_file

        is_youtube = any(domain in url.lower() for domain in ["youtube.com", "youtu.be"])
        is_instagram = "instagram.com" in url.lower()
        is_tiktok = "tiktok.com" in url.lower()

        try:
            info, downloaded_path_str = await asyncio.to_thread(_run_extract)
        except Exception as e:
            err_msg = str(e)
            if is_youtube:
                if "unavailable" in err_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This YouTube video is unavailable or has been removed. Please verify the URL and ensure the video is public."
                    )
                elif "private" in err_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This YouTube video is private. Deepfake Shield can only analyze public videos."
                    )
                elif "sign in" in err_msg.lower() or "age" in err_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This YouTube video requires sign-in or is age-restricted. Please test with an unrestricted public video."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unable to download YouTube video: {err_msg.split(':')[-1].strip()}"
                    )
            elif is_instagram:
                if "login" in err_msg.lower() or "checkpoint" in err_msg.lower() or "private" in err_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="This Instagram video is private or login-restricted. Please ensure the post/reel is publicly accessible."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unable to access Instagram video: {err_msg.split(':')[-1].strip()}"
                    )
            elif is_tiktok:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to extract TikTok video: {err_msg.split(':')[-1].strip()}"
                )

            if "Unsupported URL" in err_msg or "is not a valid URL" in err_msg:
                return None
            logger.warning(f"yt-dlp download failed: {err_msg}")
            return None

        target_file = Path(downloaded_path_str)
        if not target_file.exists() or target_file.stat().st_size == 0:
            return None

        file_size = target_file.stat().st_size
        if file_size > self.max_bytes:
            target_file.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Inspect magic bytes and compute sha256
        hasher = hashlib.sha256()
        with open(target_file, "rb") as f:
            header = f.read(64)
            hasher.update(header)
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)

        sha256_hash = hasher.hexdigest()
        ext = target_file.suffix.lower()
        storage_service.verify_magic_bytes(header, ext)

        title = info.get("title") or target_file.name
        clean_title = storage_service.sanitize_filename(title)
        mime_type = "video/mp4" if ext == ".mp4" else f"video/{ext.lstrip('.')}"
        saved_path = str(target_file).replace("\\", "/")

        # Inspect if video contains an audio stream
        has_audio = False
        try:
            import subprocess
            proc = subprocess.run([ffmpeg_exe, "-i", str(target_file)], capture_output=True, text=True, errors="ignore")
            has_audio = "Audio:" in proc.stderr
        except Exception:
            has_audio = False

        detected_type = "multimodal" if has_audio else "video"

        return (saved_path, clean_title, file_size, sha256_hash, detected_type, mime_type)

    async def _download_via_httpx(self, url: str, unique_prefix: str) -> Tuple[str, str, int, str, str, str]:
        """
        Direct HTTP streaming download for direct media files.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch media from URL. Source server returned HTTP {resp.status_code}."
                    )

                content_len = len(resp.content)
                if content_len == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="URL returned empty media content (0 bytes)."
                    )

                if content_len > self.max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Media from URL exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )

                # Ensure it is not an HTML webpage
                content_type = resp.headers.get("content-type", "").lower()
                is_html = "text/html" in content_type or resp.content.strip().startswith(b"<!DOCTYPE") or resp.content.strip().startswith(b"<html")
                if is_html:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The provided URL returned a webpage (HTML) rather than a playable video stream. Please ensure the link is a valid, publicly accessible video."
                    )

                # Determine extension from URL or content-type
                parsed = urlparse(url)
                url_path = Path(parsed.path)
                ext = url_path.suffix.lower()

                content_type = resp.headers.get("content-type", "").lower()
                if not ext or ext not in (settings.ALLOWED_VIDEO_EXTENSIONS + settings.ALLOWED_AUDIO_EXTENSIONS):
                    if "video/mp4" in content_type:
                        ext = ".mp4"
                    elif "video/webm" in content_type:
                        ext = ".webm"
                    elif "image/webp" in content_type:
                        ext = ".webp"
                    elif "image/jpeg" in content_type:
                        ext = ".jpg"
                    elif "image/png" in content_type:
                        ext = ".png"
                    else:
                        ext = ".mp4"  # Default video container

                # Verify magic bytes
                storage_service.verify_magic_bytes(resp.content[:64], ext)

                filename = url_path.stem[:40] if url_path.stem else "online_media"
                clean_filename = f"{unique_prefix}_{storage_service.sanitize_filename(filename)}{ext}"
                dest_path = self.upload_dir / clean_filename

                with open(dest_path, "wb") as f:
                    f.write(resp.content)

                sha256_hash = hashlib.sha256(resp.content).hexdigest()
                saved_path = str(dest_path).replace("\\", "/")

                detected_type = "video"
                mime_type = content_type or ("video/mp4" if ext == ".mp4" else f"video/{ext.lstrip('.')}")

                return (saved_path, f"{filename}{ext}", content_len, sha256_hash, detected_type, mime_type)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to download or process media from URL: {str(e)}"
            )

url_downloader = UrlDownloaderService()
