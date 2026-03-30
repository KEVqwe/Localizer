import shutil
import logging
import subprocess

logger = logging.getLogger(__name__)

import sys
import os
from worker.src.config import WINGET_FFMPEG_PATH

def get_ffmpeg_path() -> str:
    """
    Resolves and validates the FFmpeg executable path.
    Prioritizes full builds (Winget) over potentially broken conda versions.
    """
    # 1. Try explicit Winget full build
    if os.path.exists(WINGET_FFMPEG_PATH):
        return WINGET_FFMPEG_PATH

    # 2. Try system PATH
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        return ffmpeg_cmd
    
    # 3. Try common Conda locations as last resort
    possible_paths = [
        os.path.join(os.path.dirname(sys.executable), "Library", "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Library", "bin", "ffmpeg.exe"),
    ]
    
    for p in possible_paths:
        if os.path.exists(p):
            return p
            
    raise RuntimeError("FFmpeg is not installed or not found. Required for media processing.")

def get_ffprobe_path() -> str:
    """Resolves ffprobe by looking next to the ffmpeg binary."""
    ffmpeg_path = get_ffmpeg_path()
    
    # Try replacing extension first (Windows)
    ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
    if os.path.exists(ffprobe_path):
        return ffprobe_path
        
    # Try directory-based resolution
    dir_name = os.path.dirname(ffmpeg_path)
    for name in ["ffprobe.exe", "ffprobe"]:
        cand = os.path.join(dir_name, name)
        if os.path.exists(cand):
            return cand
            
    return "ffprobe" # Fallback to PATH

def run_ffmpeg_command(args: list) -> bool:
    """Runs a validated ffmpeg command"""
    try:
        ffmpeg_cmd = get_ffmpeg_path()
        cmd = [ffmpeg_cmd] + args
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg command failed: {e.stderr.decode('utf-8')}")
        return False

def get_media_duration(path: str) -> float:
    """
    Helper to get media (audio/video) duration in seconds using ffprobe.
    Robust against Windows path issues.
    """
    if not path or not os.path.exists(path):
        return 0.0
    try:
        ffprobe_bin = get_ffprobe_path()
        
        cmd = [
            ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dur = float(result.stdout.strip())
        return dur
    except Exception as e:
        logger.warning(f"Failed to get duration for {path}: {e}")
        return 0.0
