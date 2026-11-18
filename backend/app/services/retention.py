from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.core.config import settings
from app.models.entities import Scan, AuditLog
from app.services.storage import storage_service
import logging

logger = logging.getLogger("deepfake_shield.retention")

class DataRetentionService:
    def __init__(self):
        self.default_retention_days = settings.DATA_RETENTION_DAYS

    def get_storage_usage(self) -> dict:
        """Calculates total disk space used by uploaded media assets."""
        upload_dir = settings.UPLOAD_DIR.resolve()
        total_bytes = 0
        file_count = 0
        if upload_dir.exists():
            for p in upload_dir.glob("*"):
                if p.is_file():
                    total_bytes += p.stat().st_size
                    file_count += 1
        return {
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "file_count": file_count
        }

    async def get_retention_status(self, db: AsyncSession, retention_days: int = None) -> dict:
        """
        Queries database for retention metrics and identifies records eligible for lifecycle purge.
        """
        days = retention_days or self.default_retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Count total scans
        total_stmt = select(func.count(Scan.id))
        total_scans = (await db.execute(total_stmt)).scalar_one()

        # Count expired scans
        expired_stmt = select(func.count(Scan.id)).where(Scan.created_at < cutoff)
        expired_scans = (await db.execute(expired_stmt)).scalar_one()

        # Query oldest scan date
        oldest_stmt = select(func.min(Scan.created_at))
        oldest_date = (await db.execute(oldest_stmt)).scalar_one()

        disk_usage = self.get_storage_usage()

        return {
            "retention_policy_days": days,
            "cutoff_timestamp": cutoff.isoformat(),
            "total_scans_recorded": total_scans,
            "expired_scans_eligible_for_purge": expired_scans,
            "retained_active_scans": max(0, total_scans - expired_scans),
            "storage_disk_usage_mb": disk_usage["total_mb"],
            "storage_file_count": disk_usage["file_count"],
            "oldest_scan_date": oldest_date.isoformat() if oldest_date else None,
            "governance_status": "COMPLIANT"
        }

    async def purge_expired_records(
        self,
        db: AsyncSession,
        retention_days: int = None,
        admin_user_id: str = None
    ) -> dict:
        """
        Executes a secure compliance purge of scans older than retention_days.
        Deletes physical media files, cascade-deletes related database records, and creates an audit record.
        """
        days = retention_days or self.default_retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Retrieve expired scan records
        stmt = select(Scan).where(Scan.created_at < cutoff)
        result = await db.execute(stmt)
        expired_scans = result.scalars().all()

        purged_count = len(expired_scans)
        freed_bytes = 0

        for scan in expired_scans:
            freed_bytes += scan.file_size_bytes or 0
            # Remove physical media file
            storage_service.remove_file(scan.file_path)
            # Cascade delete in database
            await db.delete(scan)

        # Create immutable audit log entry
        audit = AuditLog(
            user_id=admin_user_id,
            action="data_retention_purge",
            resource_type="system_retention",
            resource_id="batch_purge",
            details={
                "retention_policy_days": days,
                "cutoff_timestamp": cutoff.isoformat(),
                "records_purged": purged_count,
                "estimated_freed_bytes": freed_bytes,
                "freed_mb": round(freed_bytes / (1024 * 1024), 2)
            }
        )
        db.add(audit)
        await db.commit()

        logger.info(f"Data retention purge completed: {purged_count} scans removed, {freed_bytes} bytes freed.")

        return {
            "status": "success",
            "retention_policy_days": days,
            "purged_records_count": purged_count,
            "freed_storage_mb": round(freed_bytes / (1024 * 1024), 2),
            "executed_at": datetime.now(timezone.utc).isoformat()
        }

retention_service = DataRetentionService()

