from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class HFSplitItem(BaseModel):
    dataset: str
    config: str
    split: str
    model_config = ConfigDict(from_attributes=True)

class HFSplitsResponse(BaseModel):
    dataset: str
    splits: List[HFSplitItem]
    pending: List[Any] = []
    failed: List[Any] = []
    model_config = ConfigDict(from_attributes=True)

class HFParquetResponse(BaseModel):
    dataset: str
    config: str
    split: str
    urls: List[str]
    total_files: int
    model_config = ConfigDict(from_attributes=True)

class HFRowItem(BaseModel):
    row_idx: int
    video_src: Optional[str] = None
    label_idx: int
    label_name: str
    is_deepfake: bool
    model_config = ConfigDict(from_attributes=True)

class HFRowsResponse(BaseModel):
    dataset: str
    config: str
    split: str
    offset: int
    length: int
    num_rows_total: int
    num_rows_per_page: int
    features: List[Dict[str, Any]]
    rows: List[HFRowItem]
    partial: bool = False
    model_config = ConfigDict(from_attributes=True)

class HFDatasetMetadata(BaseModel):
    dataset_id: str
    author: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = []
    splits: List[Dict[str, Any]] = []
    total_rows: int = 0
    parquet_urls: List[str] = []
    features_schema: List[Dict[str, Any]] = []
    last_synced_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class HFConnectionStatus(BaseModel):
    status: str  # 'connected', 'degraded', 'error'
    latency_ms: float
    dataset: str
    authenticated: bool
    splits_count: int
    total_rows_available: int
    message: str
    model_config = ConfigDict(from_attributes=True)

