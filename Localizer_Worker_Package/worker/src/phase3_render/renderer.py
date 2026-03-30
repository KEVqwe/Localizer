import os
import subprocess
import logging
from worker.src.utils.logger import setup_logger
from worker.src.utils.ffmpeg_manager import get_ffmpeg_path, get_media_duration, \
    get_ffprobe_path

logger = setup_logger(__name__)

# --- Volume Controls ---
BGM_VOLUME = 1.0
TTS_VOLUME = 2.0    # Boosted voice
MIX_POST_BOOST = 2.0 # amix averages signals, so we boost it back for a full sound
# ---------------------

def render_localized_video(
    source_video_path: str, bgm_path: str, tts_audio_path: str, ass_path: str, 
    output_video_path: str, subtitle_position: str = "bottom", 
    video_width: int = 1080, video_height: int = 1920,
    outro_video_path: str = None, outro_timestamp: float = None,
    is_overlay: bool = False
):
    """
    Combines video, BGM, and TTS. 
    Supports two Outro modes:
    1. Replace (is_overlay=False): Trims original at timestamp and appends template.
    2. Overlay (is_overlay=True): Layers template ON TOP of original at timestamp (alpha-blending).
    """
    logger.info(f"Starting final render for {output_video_path} (Mode: {'OVERLAY' if is_overlay else 'REPLACE'})")
    
    ffmpeg_bin = get_ffmpeg_path()
    escaped_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
    
    # Base command inputs
    cmd = [ffmpeg_bin, "-y"]
    cmd.extend(["-i", source_video_path]) # Input 0 (Full Source)
    cmd.extend(["-i", bgm_path])          # Input 1 (Clean BGM)
    cmd.extend(["-i", tts_audio_path])    # Input 2 (Localized TTS)
    
    if outro_video_path and os.path.exists(outro_video_path):
        cmd.extend(["-i", outro_video_path]) # Input 3 (Localized Outro Template)
        
        # [NEW] Backwards Alignment Logic
        total_video_duration = get_media_duration(source_video_path)
        outro_dur = get_media_duration(outro_video_path)
        
        # Use calculated timestamp if it results in a positive start time
        if total_video_duration > 0 and outro_dur > 0:
            calc_timestamp = max(0.0, total_video_duration - outro_dur)
            print(f"DEBUG: Backwards Alignment: Main({total_video_duration}s) - Outro({outro_dur}s) = Start({calc_timestamp}s)")
            active_timestamp = calc_timestamp
        else:
            active_timestamp = outro_timestamp or 0.0
            print(f"DEBUG: Fallback Alignment: {active_timestamp}s (Main: {total_video_duration}, Outro: {outro_dur})")
            
        delay_ms = int(active_timestamp * 1000)
        
        if is_overlay:
            # Case A: TRANSPARENT OVERLAY (Alpha Blending)
            # Video: Source + Subtitles + (Template scaled and delayed/enabled)
            filter_str = (
                # Subtitles on original
                f"[0:v]subtitles=filename='{escaped_ass_path}'[basev];"
                # Prep template (Scale + Pad to match main resolution)
                # Prep template (Scale + Pad + Shift PTS to active_timestamp)
                f"[3:v]scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"setpts=PTS-STARTPTS+{active_timestamp}/TB[outv_raw];"
                # Overlay template on base video starting at timestamp
                f"[basev][outv_raw]overlay=x=0:y=0:enable='between(t,{active_timestamp},99999)'[vout];"
                
                # Audio: Mix BGM + TTS, then add delayed Outro Template audio
                f"[1:a]volume={BGM_VOLUME}[bgm];[2:a]volume={TTS_VOLUME}[voice];"
                f"[bgm][voice]amix=inputs=2:duration=first,volume={MIX_POST_BOOST}[mix_base];"
                f"[3:a]adelay={delay_ms}|{delay_ms},volume=1.0[outa_delayed];"
                f"[mix_base][outa_delayed]amix=inputs=2:duration=first,volume={MIX_POST_BOOST}[aout]"
            )
        else:
            # Case B: OPAQUE REPLACEMENT (Splicing)
            # Use active_timestamp for the splice point
            filter_str = (
                # 1. Process Main Part (0 to T)
                f"[0:v]trim=end={active_timestamp},setpts=PTS-STARTPTS,subtitles=filename='{escaped_ass_path}'[mainv];"
                f"[1:a]atrim=end={active_timestamp},asetpts=PTS-STARTPTS,volume={BGM_VOLUME}[bgm_main];"
                f"[2:a]atrim=end={active_timestamp},asetpts=PTS-STARTPTS,volume={TTS_VOLUME}[voice_main];"
                f"[bgm_main][voice_main]amix=inputs=2:duration=first:dropout_transition=2,volume={MIX_POST_BOOST}[maina];"
                
                # 2. Process Outro Part (T onwards)
                f"[3:v]scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2,setsar=1[outv];"
                f"[1:a]atrim=start={active_timestamp},asetpts=PTS-STARTPTS,volume={BGM_VOLUME}[bgm_outro];"
                f"[3:a]volume=1.0[template_audio];"
                f"[bgm_outro][template_audio]amix=inputs=2:duration=first:dropout_transition=2,volume={MIX_POST_BOOST}[outa];"
                
                # 3. Concatenate
                f"[mainv][outv]concat=n=2:v=1:a=0[vout];"
                f"[maina][outa]concat=n=2:v=0:a=1[aout]"
            )
    else:
        # Case C: Standard Overlay (No Outro)
        filter_str = (
            f"[1:a]volume={BGM_VOLUME}[bgm];"
            f"[2:a]volume={TTS_VOLUME}[voice];"
            f"[bgm][voice]amix=inputs=2:duration=first:dropout_transition=2,volume={MIX_POST_BOOST}[aout];"
            f"[0:v]subtitles=filename='{escaped_ass_path}'[vout]"
        )

    cmd.extend(["-filter_complex", filter_str])
    cmd.extend(["-map", "[vout]", "-map", "[aout]"])
    cmd.extend([
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "22",
        "-c:a", "aac", "-b:a", "192k",
        output_video_path
    ])
    
    logger.info(f"Running FFmpeg: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        logger.info(f"Successfully rendered video: {output_video_path}")
        return output_video_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        raise RuntimeError(f"FFmpeg rendering error: {e.stderr}")
    except Exception as e:
        logger.error(f"Render error: {e}")
        raise
