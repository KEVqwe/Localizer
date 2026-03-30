import os
import subprocess
from worker.src.utils.gpu_manager import logger

def extract_audio_demucs(video_path: str, output_dir: str) -> str:
    """
    Isolates voices from background music using Demucs.
    Returns path to the isolated vocals audio file.
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Running Demucs on {video_path}")
    
    import sys
    cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems", "vocals", video_path, "-o", output_dir]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Demucs failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise RuntimeError(f"Demucs error: {e.stderr}") from e
    except Exception as e:
        logger.error(f"Demucs unexpected failed: {e}")
        raise
        
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    vocals_path = os.path.join(output_dir, "htdemucs", base_name, "vocals.wav")
    return vocals_path
