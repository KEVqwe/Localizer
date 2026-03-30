import os
from worker.src.utils.logger import setup_logger

logger = setup_logger(__name__)


def generate_ass(translated_json: dict, output_ass_path: str, video_width: int = 1080, video_height: int = 1920, outro_start_time: float = None, y_percent: float = None, fixed_y: int = None) -> str:
    """
    Converts translated transcription JSON into a .ass subtitle file.
    If outro_start_time is set, subtitles at or after that time are excluded.
    y_percent: 0.0 to 1.0 (float)
    fixed_y: static pixel coordinate (int)
    """
    segments = translated_json.get("transcription", translated_json.get("segments", []))
    
    # Filter out segments in the outro region
    # outro_start_time is the END time of the last non-outro segment
    if outro_start_time is not None:
        before = len(segments)
        segments = [s for s in segments if s.get("start", 0) < outro_start_time]
        logger.info(f"Outro filter: kept {len(segments)}/{before} segments (cutoff={outro_start_time:.2f}s)")
    
    # Position calculation
    fixed_cx = video_width / 2.0
    if fixed_y is not None:
        fixed_cy = fixed_y
    elif y_percent is not None:
        fixed_cy = video_height * y_percent
    else:
        fixed_cy = video_height * 0.8 # Default to bottom
    
    logger.info(f"Subtitles positioned at y={int(fixed_cy)} ({y_percent*100 if y_percent else 80:.1f}%)")
    
    # Fixed clean style
    font_size = 64
    primary_color = "&H00FFFFFF"
    outline_color = "&H00000000"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,{font_size},{primary_color},&H000000FF,{outline_color},&H00000000,1,0,0,0,100,100,0,0,1,6,1,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    with open(output_ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        for segment in segments:
            start_time = _seconds_to_ass_time(segment.get("start", 0))
            end_time = _seconds_to_ass_time(segment.get("end", 0))
            text = segment.get("text", "").strip()
            
            if not text:
                continue
                
            text = f"{{\\pos({int(fixed_cx)},{int(fixed_cy)})}}" + text
            f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
            
    logger.info(f"Generated ASS with {len(segments)} subtitles at {output_ass_path}")
    return output_ass_path

def _seconds_to_ass_time(seconds: float) -> str:
    """Converts seconds to ASS time format (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"
