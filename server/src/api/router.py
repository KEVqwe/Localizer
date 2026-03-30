from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import os
import json
import logging
import shutil
from pathlib import Path
import re # Added for smart naming

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from server.src.queue.celery_app import celery_app
from server.src.models.models import WorkerNode, WorkerStatus

router = APIRouter(prefix="/api/v1", tags=["jobs", "nodes"])

UPLOAD_DIR = Path("server/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("worker/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTRO_TEMPLATES_DIR = Path("worker/assets/outros")
OUTRO_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

active_jobs = {}
mock_nodes = [
    WorkerNode(id="PC-A", gpu_info="RTX 4080 16GB", status=WorkerStatus.IDLE),
    WorkerNode(id="PC-B", gpu_info="RTX 4070 12GB", status=WorkerStatus.BUSY)
]

class ApprovalRequest(BaseModel):
    job_id: str
    validated_subtitles: List[Dict[str, Any]]
    subtitle_position: str = "bottom"
    outro_start_time: float = None
    outro_template_id: str = None
    subtitle_y_percent: float = 0.8
    is_overlay: bool = True # Default to True (Backward-Aligned Overlay)

def _check_resolution(file_path: Path) -> bool:
    """Uses ffprobe to ensure video is 1080x1920."""
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(file_path)]
        out = subprocess.check_output(cmd, text=True).strip()
        if out == "1080x1920":
            return True
        return False
    except Exception:
        return False

import subprocess

def get_localized_filename(original_name: str, lang_code: str) -> str:
    """
    Intelligently replaces 'EN' or '_0EN_' in the original filename with the target lang.
    Example: #250512..._0EN_... -> #250512..._0RU_...
    """
    if not original_name:
        return f"{lang_code}.mp4"
        
    base, ext = os.path.splitext(original_name)
    lang_upper = lang_code.upper()
    
    # Priority 1: Match specifically _0EN_ (with any digit prefix)
    pattern = re.compile(r'_(\d+)EN_', re.IGNORECASE)
    if pattern.search(base):
        new_base = pattern.sub(f'_\\1{lang_upper}_', base)
        return f"{new_base}{ext}"
    
    # Priority 2: Generic EN replacement if it looks like a tag
    if "_EN_" in base.upper():
        new_base = re.sub(r'_EN_', f'_{lang_upper}_', base, flags=re.IGNORECASE)
        return f"{new_base}{ext}"
        
    # Fallback: Just append the language if no EN pattern found
    return f"{base}_{lang_upper}{ext}"

def get_clean_title(filename: str) -> str:
    """
    Extracts a human-readable title from complex filenames.
    Pattern: ..._9(TITLE)_0...
    """
    if not filename:
        return "Unknown Video"
        
    # Specifically target the content between _9 and the next _0
    match = re.search(r'_9(.*?)_0', filename)
    if match:
        return match.group(1).strip()
    
    # Fallback to base name without ext if no pattern
    return os.path.splitext(filename)[0]

@router.post("/jobs/submit")
async def submit_job(video_file: UploadFile = File(...)):
    """
    Initiates a new Phase 1 extraction task, dropping it into the Redis queue.
    """
    task_id = str(uuid.uuid4())
    
    # Sanitize filename: replace '#' and other troublesome characters, or just use UUID
    clean_filename = f"{task_id}_{video_file.filename.replace('#', '').replace(' ', '_')}"
    
    # Save the uploaded file
    file_path = UPLOAD_DIR / clean_filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(video_file.file, buffer)
    
    # NEW: Validate Resolution
    if not _check_resolution(file_path):
        os.remove(file_path) # Clean up invalid file
        raise HTTPException(
            status_code=400, 
            detail="非法分辨率！仅支持 1080x1920 (9:16 竖版) 的无字幕视频。"
        )

    # Pass absolute path to Celery
    abs_video_path = str(file_path.absolute())
    abs_output_path = str(OUTPUT_DIR.absolute())
    
    task = celery_app.send_task(
        "worker.src.celery_tasks.process_video",
        args=[task_id, abs_video_path, abs_output_path, video_file.filename]
    )
    
    # [FIX] Store task ID to track QUEUED vs PROCESSING status
    active_jobs[task_id] = {"status": "QUEUED", "task_id": task.id}
    
    return {
        "task_id": task_id, 
        "job_id": task_id,
        "status": "QUEUED"
    }

# Language config (must match worker/src/config.py)
LANG_NAMES = {
    "de": "German", "es": "Spanish", "fr": "French",
    "id": "Indonesian", "it": "Italian", "pl": "Polish",
    "pt": "Portuguese", "ru": "Russian", "tr": "Turkish"
}

@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Check the status of a job with per-language progress.
    """
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        return {"job_id": job_id, "status": "NOT_FOUND"}
    
    # Check per-language progress
    lang_progress = {}
    completed_count = 0
    for lang in LANG_NAMES:
        lang_dir = job_dir / lang
        if (lang_dir / "final_localized.mp4").exists():
            lang_progress[lang] = "done"
            completed_count += 1
        elif (lang_dir / "tts_audio.mp3").exists():
            lang_progress[lang] = "rendering"
        elif (lang_dir / "dubbing.lock").exists():
            lang_progress[lang] = "dubbing"
        elif (lang_dir / "translated.json").exists():
            lang_progress[lang] = "waiting_dubbing"
        elif lang_dir.exists():
            lang_progress[lang] = "translating"
        else:
            lang_progress[lang] = "waiting"
    
    total = len(LANG_NAMES)
    
    # Determine overall status
    if completed_count == total:
        return {"job_id": job_id, "status": "COMPLETED", "progress": lang_progress, "completed": completed_count, "total": total}
    
    # [NEW] Prioritize Phase 2 detection to prevent UI jumps
    # If transcription_validated exists, we are committed to Step 4 (GENERATING)
    if (job_dir / "transcription_validated.json").exists():
        return {"job_id": job_id, "status": "GENERATING", "progress": lang_progress, "completed": completed_count, "total": total}

    # [NEW] Check if Phase 1A complete (transcription ready for review)
    trans_path = job_dir / "transcription.json"
    if trans_path.exists():
        return {"job_id": job_id, "status": "WAITING_FOR_REVIEW"}

    # Check if currently processing in Celery or waiting in queue
    status_info = active_jobs.get(job_id)
    if status_info:
        task_id = status_info.get("task_id")
        if task_id:
            res = celery_app.AsyncResult(task_id)
            if res.status == 'PENDING':
                return {"job_id": job_id, "status": "QUEUED", "progress": lang_progress, "completed": completed_count, "total": total}
            if res.status in ['STARTED', 'RETRY', 'PROGRESS']:
                # The marker checks above handle Phase 2, so here we must be in Phase 1
                return {"job_id": job_id, "status": "PROCESSING", "progress": lang_progress, "completed": completed_count, "total": total}

    # Default fall-through for early Phase 1
    if status_info:
        return {"job_id": job_id, "status": "QUEUED", "progress": lang_progress}
        
    return {"job_id": job_id, "status": "PROCESSING"}

@router.get("/jobs/{job_id}/transcription")
async def get_job_transcription(job_id: str):
    """
    Returns the extracted transcription for the user to review.
    """
    job_dir = OUTPUT_DIR / job_id
    trans_path = job_dir / "transcription.json"
    
    if not trans_path.exists():
        raise HTTPException(status_code=404, detail="Transcription not ready yet.")
    
    with trans_path.open("r", encoding='utf-8') as f:
        return json.load(f)

@router.post("/jobs/approve/{task_id}")
async def approve_job(task_id: str, request: ApprovalRequest):
    """
    User confirms the validated transcription (subtitles),
    triggering Phase 2: Translation + TTS + SRT for 9 languages.
    """
    job_dir = str(OUTPUT_DIR.absolute() / request.job_id)
    
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail=f"Job directory not found: {request.job_id}")
    
    # Physically remove segments that start after the outro cutoff
    filtered_subtitles = request.validated_subtitles
    if request.outro_start_time is not None:
        filtered_subtitles = [s for s in request.validated_subtitles if s.get("start", 0) < (request.outro_start_time - 0.01)]
        logger.info(f"Filtering job {request.job_id}: {len(request.validated_subtitles)} -> {len(filtered_subtitles)} segments")

    # Save the human-validated transcription
    validated_path = os.path.join(job_dir, "transcription_validated.json")
    with open(validated_path, 'w', encoding='utf-8') as f:
        json.dump({"segments": filtered_subtitles}, f, indent=2, ensure_ascii=False)
    
    # Trigger Phase 2 via Celery
    task = celery_app.send_task(
        "worker.src.celery_tasks.process_phase2",
        args=[
            job_dir, validated_path, request.subtitle_position, 
            request.outro_start_time, request.outro_template_id, 
            request.subtitle_y_percent, request.is_overlay
        ]
    )
    
    active_jobs[request.job_id] = {"status": "IN_PROGRESS_PHASE_2", "task_id": task.id}
    return {
        "job_id": request.job_id,
        "celery_task_id": task.id,
        "status": "GENERATING"
    }

@router.post("/jobs/{job_id}/abort")
async def abort_job(job_id: str):
    """
    Aborts a running or queued job and physically deletes its directory.
    """
    status_info = active_jobs.get(job_id)
    task_id = status_info.get("task_id") if status_info else None
    
    logger.info(f"Aborting job {job_id} (Celery Task: {task_id})")
    
    # 1. Revoke Celery task if it exists
    if task_id:
        try:
            celery_app.control.revoke(task_id, terminate=True)
        except Exception as e:
            logger.warning(f"Failed to revoke task {task_id}: {e}")
    
    # 2. Physically delete the job directory
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists() and job_dir.is_dir():
        try:
            # We use a small delay or retry if needed for Windows file locks, 
            # but usually rmtree is fine after revoke.
            shutil.rmtree(job_dir)
            logger.info(f"Deleted job directory: {job_dir}")
        except Exception as e:
            logger.error(f"Failed to delete job directory {job_dir}: {e}")
            # Even if deletion fails (e.g. file lock), we still want to clear from memory
    
    # 3. Clear from memory
    if job_id in active_jobs:
        del active_jobs[job_id]
        
    return {"job_id": job_id, "status": "ABORTED", "deleted": True}

@router.get("/jobs")
async def list_jobs():
    """
    Lists all historical jobs by scanning the outputs directory.
    """
    if not OUTPUT_DIR.exists():
        return {"jobs": []}
    
    jobs = []
    # Sort by directory modification time (newest first)
    dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True
    )
    
    for job_dir in dirs:
        job_id = job_dir.name
        metadata_path = job_dir / "job_metadata.json"
        
        # [NEW] Requirement: Only show folders with metadata & source video
        # This filters out partial Demucs folders or failed initialization folders
        if not metadata_path.exists() or not (job_dir / "source_video.mp4").exists():
            continue
            
        filename = "Unknown Video"
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                filename = meta.get("filename", filename)
        except: pass
            
        # Determine approximate status for list view
        status = "UNKNOWN"
        if (job_dir / "final_localized.mp4").exists() or (job_dir / "de" / "final_localized.mp4").exists():
            status = "COMPLETED"
        elif (job_dir / "transcription_validated.json").exists():
            status = "GENERATING"
        elif (job_dir / "transcription.json").exists():
            status = "WAITING_FOR_REVIEW"
        else:
            status = "PROCESSING"
            
        jobs.append({
            "job_id": job_id,
            "filename": filename,
            "display_name": get_clean_title(filename),
            "status": status,
            "created_at": job_dir.stat().st_mtime
        })
        
    return {"jobs": jobs[:20]} # Return last 20 jobs

@router.get("/jobs/{job_id}/original-video")
async def get_original_video(job_id: str):
    """
    Serves the original source video for frontend preview and positioning.
    """
    output_dir = OUTPUT_DIR / job_id
    video_path = output_dir / "source_video.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Original video not found.")
        
    return FileResponse(str(video_path.absolute()), media_type="video/mp4")

@router.get("/jobs/outro-templates")
async def list_outro_templates():
    """
    Lists available outro templates by scanning the assets/outros directory.
    """
    if not OUTRO_TEMPLATES_DIR.exists():
        return {"templates": []}
    
    templates = [d.name for d in OUTRO_TEMPLATES_DIR.iterdir() if d.is_dir()]
    return {"templates": sorted(templates)}

@router.get("/jobs/{job_id}/download-all")
async def download_all_videos(job_id: str):
    """
    Packages all localized videos into a single ZIP file and returns it.
    """
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job directory not found.")
    
    zip_filename = "all_localized.zip"
    zip_path = job_dir / zip_filename
    
    # Optional: If it already exists, just return it (unless you want to force re-zip)
    if zip_path.exists():
        # Check if it's stale? For now, just return.
        pass
    
    import zipfile
    from worker.src.config import TARGET_LANGUAGES
    
    found_any = False
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for lang in TARGET_LANGUAGES:
                # Look in language subfolder
                lang_vid = job_dir / lang / "final_localized.mp4"
                if lang_vid.exists():
                    # Use smart naming for the file inside the ZIP
                    original_name = "video.mp4"
                    metadata_path = job_dir / "job_metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                original_name = meta.get("filename", original_name)
                        except: pass
                    
                    smart_name = get_localized_filename(original_name, lang)
                    zf.write(lang_vid, arcname=smart_name)
                    found_any = True
        
        if not found_any:
            if zip_path.exists(): zip_path.unlink()
            raise HTTPException(status_code=404, detail="No localized videos found to package.")
            
        # Get original filename for the response header if possible
        display_name = "localized_videos.zip"
        metadata_path = job_dir / "job_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    orig = meta.get("filename", "video")
                    name_base = os.path.splitext(orig)[0]
                    display_name = f"localized_{name_base}.zip"
            except: pass
            
        return FileResponse(
            zip_path, 
            media_type="application/zip", 
            filename=display_name
        )
    except Exception as e:
        logger.error(f"Failed to create ZIP for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {str(e)}")

@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Returns the list of available localized videos for download.
    """
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    languages = []
    for lang_code, lang_name in LANG_NAMES.items():
        final_vid = job_dir / lang_code / "final_localized.mp4"
        if final_vid.exists():
            languages.append({
                "lang_code": lang_code,
                "lang_name": lang_name,
                "download_url": f"/api/v1/jobs/{job_id}/download/{lang_code}"
            })
    
    return {"job_id": job_id, "languages": languages}

@router.get("/jobs/{job_id}/download/{lang_code}")
async def download_video(job_id: str, lang_code: str):
    """
    Serves the final localized video file for download.
    """
    job_dir = OUTPUT_DIR / job_id
    video_path = job_dir / lang_code / "final_localized.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video not found for language: {lang_code}")
    
    # Use smart naming
    original_name = "video.mp4"
    metadata_path = job_dir / "job_metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                original_name = meta.get("filename", original_name)
        except: pass
    
    smart_name = get_localized_filename(original_name, lang_code)
    
    return FileResponse(
        path=str(video_path.absolute()),
        media_type="video/mp4",
        filename=smart_name
    )

@router.get("/nodes/status")
async def get_nodes_status():
    """
    Returns the status of all available local workers on the LAN.
    """
    return {
        "total_nodes": len(mock_nodes),
        "nodes": [node.dict() for node in mock_nodes]
    }
