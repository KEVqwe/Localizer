import cv2
import numpy as np
import os
from worker.src.utils.logger import setup_logger

logger = setup_logger(__name__)

def extract_first_frame(video_path: str) -> np.ndarray:
    """Extracts the very first frame of a video."""
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    if not success:
        raise ValueError(f"Could not read first frame from {video_path}")
    return frame

def find_anchor_timestamp(video_path: str, anchor_frame: np.ndarray, search_start_s: float, search_window_s: float = 4.0) -> float:
    """
    Searches for an anchor_frame in a video within a specific time window.
    Returns the exact timestamp (seconds) of the best match.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    start_frame = int(max(0, (search_start_s - search_window_s/2) * fps))
    end_frame = int((search_start_s + search_window_s/2) * fps)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    best_val = -1
    best_timestamp = search_start_s
    
    # Resize anchor for faster matching if needed, but here we prefer accuracy
    # Template matching is sensitive to resolution, so we assume they match 1080p
    
    current_frame_idx = start_frame
    while current_frame_idx < end_frame:
        success, frame = cap.read()
        if not success:
            break
            
        # Use TM_CCOEFF_NORMED for robust matching (range 0 to 1)
        res = cv2.matchTemplate(frame, anchor_frame, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val > best_val:
            best_val = max_val
            best_timestamp = current_frame_idx / fps
            
        # If we find a near-perfect match, stop early to save time
        if best_val > 0.98:
            logger.info(f"Excellent anchor match found: {best_val:.4f} at {best_timestamp:.3f}s")
            break
            
        current_frame_idx += 1
        
    cap.release()
    
    if best_val < 0.8:
        logger.warning(f"Weak anchor match ({best_val:.4f}). Falling back to manual timestamp: {search_start_s}s")
        return search_start_s
        
    return best_timestamp
