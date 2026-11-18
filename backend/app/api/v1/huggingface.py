from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import Optional
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.entities import User, DatasetMetadata, AuditLog
from app.schemas.huggingface import (
    HFConnectionStatus,
    HFSplitsResponse,
    HFParquetResponse,
    HFRowsResponse,
    HFDatasetMetadata,
)
from app.services.huggingface import hf_service

router = APIRouter()

@router.get("/status", response_model=HFConnectionStatus)
async def get_connection_status(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    current_user: User = Depends(get_current_user)
):
    """
    Checks real-time connectivity and latency to Hugging Face Datasets Server API.
    """
    res = await hf_service.check_connection(dataset)
    return HFConnectionStatus(**res)

@router.get("/splits", response_model=HFSplitsResponse)
async def get_dataset_splits(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint 1: Retrieves dataset split information from Hugging Face Datasets Server.
    """
    res = await hf_service.get_splits(dataset)
    return HFSplitsResponse(**res)

@router.get("/parquet", response_model=HFParquetResponse)
async def get_parquet_files(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    config: str = Query("default", description="Dataset config name"),
    split: str = Query("train", description="Dataset split name"),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint 3: Retrieves Parquet file URLs and partitioning metadata.
    """
    res = await hf_service.get_parquet(dataset=dataset, config=config, split=split)
    return HFParquetResponse(**res)

@router.get("/rows", response_model=HFRowsResponse)
async def get_dataset_rows(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    config: str = Query("default", description="Dataset config name"),
    split: str = Query("train", description="Dataset split name"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
    length: int = Query(20, ge=1, le=100, description="Number of rows to retrieve (max 100)"),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint 2: Retrieves dataset sample rows with configurable offset and length.
    Maps ground-truth labels and extracts raw video references.
    """
    res = await hf_service.get_rows(
        dataset=dataset,
        config=config,
        split=split,
        offset=offset,
        length=length
    )
    return HFRowsResponse(**res)

@router.get("/metadata", response_model=HFDatasetMetadata)
async def get_metadata(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves comprehensive dataset metadata (checking DB cache first before calling HF API).
    """
    ds = dataset or hf_service.default_dataset

    # Check local database cache first
    stmt = select(DatasetMetadata).where(DatasetMetadata.dataset_id == ds)
    res = await db.execute(stmt)
    meta = res.scalars().first()

    if meta:
        return HFDatasetMetadata(
            dataset_id=meta.dataset_id,
            author=meta.author,
            description=meta.description,
            license=meta.license,
            tags=meta.tags or [],
            splits=meta.splits or [],
            total_rows=meta.total_rows,
            parquet_urls=meta.parquet_urls or [],
            features_schema=meta.features_schema or [],
            last_synced_at=meta.last_synced_at,
        )

    # If not in DB, fetch live and save
    live_meta = await hf_service.get_dataset_metadata(ds)
    now = datetime.now(timezone.utc)

    meta = DatasetMetadata(
        dataset_id=ds,
        author=live_meta["author"],
        description=live_meta["description"],
        license=live_meta["license"],
        tags=live_meta["tags"],
        splits=live_meta["splits"],
        total_rows=live_meta["total_rows"],
        parquet_urls=live_meta["parquet_urls"],
        features_schema=live_meta["features_schema"],
        last_synced_at=now,
    )
    db.add(meta)
    await db.commit()
    await db.refresh(meta)

    return HFDatasetMetadata(
        dataset_id=meta.dataset_id,
        author=meta.author,
        description=meta.description,
        license=meta.license,
        tags=meta.tags or [],
        splits=meta.splits or [],
        total_rows=meta.total_rows,
        parquet_urls=meta.parquet_urls or [],
        features_schema=meta.features_schema or [],
        last_synced_at=meta.last_synced_at,
    )

@router.post("/sync", response_model=HFDatasetMetadata)
async def sync_dataset_metadata(
    dataset: Optional[str] = Query(None, description="Hugging Face dataset identifier"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Force-syncs fresh metadata from Hugging Face into PostgreSQL/database.
    """
    ds = dataset or hf_service.default_dataset
    hf_service.clear_cache()
    live_meta = await hf_service.get_dataset_metadata(ds)
    now = datetime.now(timezone.utc)

    stmt = select(DatasetMetadata).where(DatasetMetadata.dataset_id == ds)
    res = await db.execute(stmt)
    meta = res.scalars().first()

    if not meta:
        meta = DatasetMetadata(dataset_id=ds)
        db.add(meta)

    meta.author = live_meta["author"]
    meta.description = live_meta["description"]
    meta.license = live_meta["license"]
    meta.tags = live_meta["tags"]
    meta.splits = live_meta["splits"]
    meta.total_rows = live_meta["total_rows"]
    meta.parquet_urls = live_meta["parquet_urls"]
    meta.features_schema = live_meta["features_schema"]
    meta.last_synced_at = now

    audit = AuditLog(
        user_id=current_user.id,
        action="hf_dataset_metadata_synced",
        resource_type="dataset",
        resource_id=ds,
        details={"total_rows": meta.total_rows, "splits": len(meta.splits)}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(meta)

    return HFDatasetMetadata(
        dataset_id=meta.dataset_id,
        author=meta.author,
        description=meta.description,
        license=meta.license,
        tags=meta.tags or [],
        splits=meta.splits or [],
        total_rows=meta.total_rows,
        parquet_urls=meta.parquet_urls or [],
        features_schema=meta.features_schema or [],
        last_synced_at=meta.last_synced_at,
    )

