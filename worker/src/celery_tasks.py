from server.src.queue.celery_app import celery_app
from worker.src.phase1_gpu.pipeline import run_phase1_extract_only
from worker.src.phase2_api.pipeline import run_phase2_generation
from worker.src.utils.logger import setup_logger

logger = setup_logger(__name__)

@celery_app.task(name="worker.src.celery_tasks.process_video", bind=True)
def process_video(self, job_id: str, video_path: str, output_base_dir: str, original_filename: str = None):
    """
    Phase 1: Extract audio (Demucs) + Transcribe (WhisperX).
    """
    logger.info(f"Celery extraction start for {job_id}: {video_path} ({original_filename})")
    result = run_phase1_extract_only(job_id, video_path, output_base_dir, original_filename=original_filename)
    return result


@celery_app.task(name="worker.src.celery_tasks.process_phase2", bind=True)
def process_phase2(self, job_dir: str, transcription_json_path: str, subtitle_position: str = "bottom", outro_start_time: float = None, outro_template_id: str = None, subtitle_y_percent: float = 0.8, is_overlay: bool = True):
    """
    Phase 2 (Translate + TTS + Render).
    """
    logger.info(f"Celery Phase 2 start for job: {job_dir} (Template: {outro_template_id}, Overlay: {is_overlay})")
    
    # Directly run generation
    result = run_phase2_generation(
        job_dir, transcription_json_path, 
        subtitle_position, 
        outro_start_time=outro_start_time, 
        outro_template_id=outro_template_id,
        subtitle_y_percent=subtitle_y_percent,
        is_overlay=is_overlay
    )
    return result

