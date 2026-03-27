# API Contracts: Auto Video Localizer (LAN GPU Edition)

## `POST /api/v1/jobs/submit`
Initiates a new Phase 1 extraction task, dropping it into the Redis queue.

**Request Form Data:**
- `video_file`: File (MP4/MOV)

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "QUEUED"
}
```

## `GET /api/v1/tasks/{task_id}`
Returns the progress of the GPU extraction.

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "DONE",
  "assigned_worker": "DELL-WORKSTATION-01",
  "results": {
    "subtitles": [ ... ],
    "ui_elements": [ ... ]
  }
}
```

## `POST /api/v1/jobs/approve/{task_id}`
User confirms the validated JSON (subtitles, UI elements), triggering the Phase 2 & 3 API translations and 9-language rendering.

**Request Body:**
```json
{
  "validated_subtitles": [ ... ],
  "validated_ui_elements": [ ... ]
}
```

**Response:**
```json
{
  "localization_job_id": "uuid-string",
  "status": "IN_PROGRESS_PHASE_2"
}
```

## `GET /api/v1/nodes/status`
Returns the status of all available local workers on the LAN.

**Response:**
```json
{
  "total_nodes": 3,
  "nodes": [
    {
      "hostname": "PC-A",
      "gpu": "RTX 4080 16GB",
      "status": "IDLE"
    },
    {
      "hostname": "PC-B",
      "gpu": "RTX 4070 12GB",
      "status": "BUSY"
    }
  ]
}
```
