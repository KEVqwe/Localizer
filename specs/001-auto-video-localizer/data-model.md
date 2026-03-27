# Data Model: Auto Video Localizer (LAN GPU Edition)

## Entities

### `VideoAsset`
Represents the uploaded original English video.
- `id`: string (UUID)
- `filename`: string
- `duration_seconds`: float
- `status`: enum (`UPLOADING`, `EXTRACTING`, `WAITING_VALIDATION`, `VALIDATED`, `GENERATING`, `DONE`, `FAILED`)
- `created_at`: datetime

### `WorkerNode`
Represents the client machines connected to the LAN Redis server.
- `id`: string (UUID or hostname)
- `gpu_info`: string (e.g. `RTX 4070 12GB`)
- `status`: enum (`IDLE`, `BUSY`, `OFFLINE`)
- `current_job_id`: string (optional)

### `Phase1ExtractionTask`
Task representation for the VRAM-heavy GPU operations.
- `id`: string (UUID)
- `video_asset_id`: string (UUID)
- `worker_id`: string (Assigned Node)
- `status`: enum (`QUEUED`, `RUNNING`, `DONE`, `ERROR`)
- `demucs_output_path`: string
- `whisper_json_path`: string
- `qwen_ui_coords_path`: string

### `LocalizationJob`
Tracks the global state of the 9-language generation process (Phases 2 & 3).
- `id`: string (UUID)
- `video_asset_id`: string (UUID)
- `target_languages`: list[string]
- `status`: enum (`PENDING_APPROVAL`, `APPROVED`, `IN_PROGRESS`, `DONE`)

### `LocalizedVideo`
Represents the individual generated video for one target language.
- `id`: string (UUID)
- `job_id`: string (UUID)
- `language_code`: string
- `status`: enum (`PENDING`, `TRANSLATING`, `DUBBING`, `RENDERING`, `DONE`, `ERROR`)
- `output_path`: string

## State Transitions
1. **GPU Extraction**: User Uploads Video -> `Phase1ExtractionTask` enqueued in Redis -> Idle `WorkerNode` processes (Serial VRAM loads/unloads) -> Stores JSONs -> `WAITING_VALIDATION`.
2. **Review**: User validates/edits extracted English text/UI -> `VALIDATED` -> Spawns 9 `LocalizedVideo` tasks.
3. **Generation**: `LocalizationJob` starts. CPU/API run `TRANSLATING` & `DUBBING`. 
4. **Rendering**: Local GPU runs `RENDERING` (NVENC) mixing streams.
