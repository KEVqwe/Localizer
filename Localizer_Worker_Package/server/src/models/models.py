from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class VideoAssetStatus(str, Enum):
    UPLOADING = "UPLOADING"
    EXTRACTING = "EXTRACTING"
    WAITING_VALIDATION = "WAITING_VALIDATION"
    VALIDATED = "VALIDATED"
    GENERATING = "GENERATING"
    DONE = "DONE"
    FAILED = "FAILED"

class VideoAsset(BaseModel):
    id: str
    filename: str
    duration_seconds: float
    status: VideoAssetStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"

class WorkerNode(BaseModel):
    id: str
    gpu_info: str
    status: WorkerStatus
    current_job_id: Optional[str] = None

class ExtractionTaskStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"

class Phase1ExtractionTask(BaseModel):
    id: str
    video_asset_id: str
    worker_id: Optional[str] = None
    status: ExtractionTaskStatus
    demucs_output_path: Optional[str] = None
    whisper_json_path: Optional[str] = None

class JobStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class LocalizationJob(BaseModel):
    id: str
    video_asset_id: str
    target_languages: List[str]
    status: JobStatus

class LocalizedVideoStatus(str, Enum):
    PENDING = "PENDING"
    TRANSLATING = "TRANSLATING"
    DUBBING = "DUBBING"
    RENDERING = "RENDERING"
    DONE = "DONE"
    ERROR = "ERROR"

class LocalizedVideo(BaseModel):
    id: str
    job_id: str
    language_code: str
    status: LocalizedVideoStatus
    output_path: Optional[str] = None
