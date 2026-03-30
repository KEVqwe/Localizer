import os
import shutil
from worker.src.phase1_gpu.demucs_extractor import extract_audio_demucs
from worker.src.phase1_gpu.whisper_transcriber import transcribe_audio
from worker.src.utils.gpu_manager import logger, free_vram


def run_phase1_extract_only(job_id: str, video_path: str, output_base_dir: str, original_filename: str = None) -> dict:
    """
    Phase 1: Demucs audio separation + WhisperX transcription.
    No visual processing needed — user uploads clean video.
    """
    job_dir = os.path.join(output_base_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save metadata
    if original_filename:
        import json
        with open(os.path.join(job_dir, "job_metadata.json"), 'w', encoding='utf-8') as f:
            json.dump({"job_id": job_id, "filename": original_filename}, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Starting Phase 1 for {video_path}")
    
    # Copy source video to job directory
    source_video_copy = os.path.join(job_dir, "source_video.mp4")
    shutil.copy2(video_path, source_video_copy)
    
    free_vram()
    
    try:
        # Step 1: Demucs — separate vocals from BGM
        vocals_path = extract_audio_demucs(video_path, os.path.join(job_dir, "audio"))
        free_vram()
        
        # Step 2: WhisperX — speech-to-text with word-level timestamps
        whisper_json_path = os.path.join(job_dir, "transcription.json")
        transcribe_audio(vocals_path, whisper_json_path)
        free_vram()
        
        return {
            "status": "WAITING_FOR_REVIEW",
            "job_id": job_id,
            "transcription_path": whisper_json_path,
            "video_path": source_video_copy
        }
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        return {"status": "ERROR", "message": str(e)}
