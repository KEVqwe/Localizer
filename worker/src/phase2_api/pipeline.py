import os
import json
import re
import subprocess

# Silence HuggingFace symlinks warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from concurrent.futures import ThreadPoolExecutor, as_completed
from worker.src.config import TARGET_LANGUAGES, LANGUAGE_NAMES, DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT
from worker.src.phase2_api.translator import translate_content
from worker.src.phase2_api.tts_generator import generate_tts_elevenlabs, MALE_VOICE_ID, FEMALE_VOICE_ID, VOICE_PERSONA_REGISTRY
from worker.src.phase3_render.renderer import render_localized_video
from worker.src.utils.logger import setup_logger
from worker.src.utils.audio_utils import mix_tts_audio
from worker.src.utils.ffmpeg_manager import get_ffprobe_path, get_media_duration
from google import genai
from google.genai import types

logger = setup_logger(__name__)

# Max parallel languages (reduced from 9 to 5 to prevent VRAM and API contention)
MAX_PARALLEL = 5

def _probe_video_dimensions(video_path: str) -> tuple:
    """Detects video resolution using ffprobe."""
    if not video_path or not os.path.exists(video_path):
        return DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT
    try:
        ffprobe_bin = get_ffprobe_path()
        cmd = [ffprobe_bin, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]
        out = subprocess.check_output(cmd, text=True).strip()
        if 'x' in out:
            w, h = out.split('x')
            return int(w), int(h)
    except Exception as e:
        logger.warning(f"Could not probe video dims: {e}")
    return DEFAULT_VIDEO_WIDTH, DEFAULT_VIDEO_HEIGHT



def process_single_language(
    lang_code: str, job_dir: str, structured_segments: list,
    bgm_path: str, source_video_path: str, subtitle_position: str,
    video_width: int, video_height: int,
    cloned_voice_id: str = None, outro_start_time: float = None,
    outro_video_template_path: str = None,
    subtitle_y_percent: float = 0.8,
    is_overlay: bool = False
) -> dict:
    """Processes all steps for a single target language."""
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
    lang_dir = os.path.join(job_dir, lang_code)
    os.makedirs(lang_dir, exist_ok=True)
    
    logger.info(f"Processing language: {lang_name} ({lang_code})")
    
    # Step 1: Translate
    translated_raw = translate_content(structured_segments, lang_name)
    
    # Process proportional timestamps for semantic chunks
    translated_structured = {"transcription": []}
    for item in translated_raw:
        start_t = item.get("start", 0.0)
        end_t = item.get("end", 1.0)
        dur = end_t - start_t
        chunks_str = item.get("chunks", [])
        
        if not chunks_str or not isinstance(chunks_str, list):
            chunks_str = [item.get("full_text", "")]
            
        merged = []
        for c in chunks_str:
            c = c.strip()
            if not c: continue
            if len(c.split()) <= 1 and merged:
                merged[-1] += " " + c
            else:
                merged.append(c)
        if len(merged) > 1 and len(merged[0].split()) <= 1:
            merged[1] = merged[0] + " " + merged[1]
            merged.pop(0)
        chunks_str = merged
            
        total_chars = sum(len(c.strip()) for c in chunks_str)
        curr_time = start_t
        
        chunk_objs = []
        for i, c in enumerate(chunks_str):
            t_len = len(c.strip())
            c_dur = dur * (t_len / total_chars) if total_chars else 0
            
            # Subtitle Overlap Fix: Subtract gap (0.07s) from end, except possibly the last one if we want 
            # to be truly precise, but 0.07s is small enough to apply generally for flicker prevention.
            c_end = curr_time + c_dur
            if i < len(chunks_str) - 1:
                # Create a small gap before the next chunk starts
                c_end_padded = max(curr_time, round(c_end - 0.07, 3))
            else:
                c_end_padded = round(c_end, 3)

            chunk_objs.append({
                "text": c.strip(),
                "start": round(curr_time, 3),
                "end": c_end_padded
            })
            curr_time += c_dur
            
        translated_structured["transcription"].append({
            "full_text": item.get("full_text", ""),
            "start": start_t, # Preserve global sentence start
            "end": start_t + dur, # Preserve global sentence end
            "chunks": chunk_objs
        })
        
    translated_json_path = os.path.join(lang_dir, "translated.json")
    with open(translated_json_path, 'w', encoding='utf-8') as f:
        json.dump(translated_structured, f, indent=2, ensure_ascii=False)
    
    # Step 2: Mix TTS Audio (Generate Audio & Align Words!)
    from pydub import AudioSegment
    from worker.src.utils.ffmpeg_manager import get_ffmpeg_path
    AudioSegment.converter = get_ffmpeg_path()
    
    if bgm_path and os.path.exists(bgm_path):
        total_duration_ms = len(AudioSegment.from_file(bgm_path))
    else:
        # Fallback estimation if no BGM
        total_duration_ms = int(max(item["end"] for item in translated_structured["transcription"]) * 1000) + 2000
        
    tts_path = os.path.join(lang_dir, "tts_audio.mp3")
    
    # mix_tts_audio now updates chunks internally with WhisperX alignments
    mix_tts_audio(
        translated_structured.get("transcription", []),
        tts_path, total_duration_ms,
        voice_id=cloned_voice_id,
        language_code=lang_code
    )
    
    # Step 3: Generate ASS subtitles (using the now-aligned chunks)
    flat_translated = [
        chunk for item in translated_structured.get("transcription", [])
        for chunk in item.get("chunks", [])
    ]
    
    # [NEW] Enforce strict gap (0.07s) and apply lead offset (-0.1s)
    SUBTITLE_OFFSET = -0.1
    for i in range(len(flat_translated)):
        chunk = flat_translated[i]
        # Apply offset
        s = round(max(0.0, float(chunk.get("start", 0.0)) + SUBTITLE_OFFSET), 3)
        e = round(max(0.0, float(chunk.get("end", 0.0)) + SUBTITLE_OFFSET), 3)
        
        # Enforce gap with NEXT chunk to prevent flickering/overlap
        if i < len(flat_translated) - 1:
            next_s = round(max(0.0, float(flat_translated[i+1].get("start", 0.0)) + SUBTITLE_OFFSET), 3)
            # Cap end time to at least 0.07s before next start
            e = min(e, max(s, round(next_s - 0.07, 3)))
            
        chunk["start"] = s
        chunk["end"] = e
            
    ass_path = os.path.join(lang_dir, "subtitles.ass")
    from worker.src.phase2_api.srt_generator import generate_ass
    generate_ass(
        {"transcription": flat_translated}, ass_path,
        video_width, video_height,
        outro_start_time=outro_start_time,
        y_percent=subtitle_y_percent
    )
    
    # Step 4: Render final video
    final_video = None
    if bgm_path and source_video_path and os.path.exists(source_video_path):
        output_video_path = os.path.join(lang_dir, "final_localized.mp4")
        try:
            render_localized_video(
                source_video_path, bgm_path, tts_path, ass_path,
                output_video_path, subtitle_position, video_width, video_height,
                outro_video_path=outro_video_template_path, 
                outro_timestamp=None, # Renderer calculates using 'Backwards Alignment'
                is_overlay=is_overlay
            )
            final_video = output_video_path
        except Exception as render_err:
            logger.error(f"Render failed for {lang_code}: {render_err}")
            
    return {
        "status": "DONE",
        "translated_json": translated_json_path,
        "subtitles_ass": ass_path,
        "tts_audio": tts_path,
        "final_video": final_video
    }


def _detect_speaker_persona(vocals_path: str) -> str:
    """
    Uses Gemini 2.5 Flash to detect the speaker's 'persona' (vibe/pitch).
    Maps to: male_deep, male_energetic, female_soft, female_young.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found for persona detection. Defaulting to female_soft.")
        return "female_soft"
        
    if not vocals_path or not os.path.exists(vocals_path):
        return "female_soft"
        
    try:
        client = genai.Client(api_key=api_key)
        logger.info(f"Analyzing speaker persona for {os.path.basename(vocals_path)} using Gemini...")
        
        # Upload to Gemini (Multimodal Audio)
        file_obj = client.files.upload(file_path=vocals_path)
        
        prompt = """
        Listen to this audio. Categorize the speaker into exactly one of these categories:
        - male_deep: Mature, low-pitched, or calm male voice.
        - male_energetic: High-energy, enthusiastic, or youthful male voice.
        - female_soft: Mature, professional, or calm female voice.
        - female_young: High-pitched, youthful, or very energetic female voice.
        
        Answer with ONLY the category name.
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(file_uri=file_obj.uri, mime_type="audio/wav"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        
        raw_text = response.text.strip().lower()
        
        # Validation against registry
        match = "male_energetic" # Default
        for p_key in VOICE_PERSONA_REGISTRY.keys():
            if p_key in raw_text:
                match = p_key
                break
            
        logger.info(f"Gemini speaker persona result: {match}")
        
        # Cleanup file from Gemini Cloud
        try: client.files.delete(name=file_obj.name)
        except: pass
        
        return match
    except Exception as e:
        logger.error(f"Persona detection failed: {e}. Defaulting to female_soft.")
        return "female_soft"


def run_phase2_generation(
    job_dir: str, transcription_json_path: str,
    subtitle_position: str = "bottom", outro_start_time: float = None,
    outro_template_id: str = None, subtitle_y_percent: float = 0.8,
    is_overlay: bool = True
) -> dict:
    """Orchestrates Phase 2: parallel translation + TTS + rendering for all languages."""
    logger.info(f"Starting Phase 2 for job: {job_dir}")
    
    source_video_path = os.path.join(job_dir, "source_video.mp4")
    
    # Find BGM and Vocals from Demucs output
    bgm_path = None
    vocals_path = None
    demucs_base = os.path.join(job_dir, "audio", "htdemucs")
    if os.path.isdir(demucs_base):
        for d in os.listdir(demucs_base):
            cand_bgm = os.path.join(demucs_base, d, "no_vocals.wav")
            if os.path.exists(cand_bgm):
                bgm_path = cand_bgm
            cand_voc = os.path.join(demucs_base, d, "vocals.wav")
            if os.path.exists(cand_voc):
                vocals_path = cand_voc
                
    # 1. Persona Detection & Voice Selection
    persona = _detect_speaker_persona(vocals_path)
    voice_id = VOICE_PERSONA_REGISTRY.get(persona, FEMALE_VOICE_ID)
    logger.info(f"Selected Persona: {persona.upper()} -> Voice ID: {voice_id}")
    
    # 2. Transcription Expansion
    video_width, video_height = _probe_video_dimensions(source_video_path)
    total_video_dur = get_media_duration(source_video_path)

    # OUTRO TEMPLATE RESOLUTION
    # No more visual matching needed! We use 'Backwards Alignment' (Duration-based).
    template_videos = {} # lang -> absolute_path
    if outro_template_id:
        template_dir = os.path.join("worker", "assets", "outros", outro_template_id)
        if os.path.isdir(template_dir):
            for lang_code in TARGET_LANGUAGES:
                # Support both .mp4 and .mov (Transparent templates are often .mov)
                found_vid = None
                for ext in [".mp4", ".mov", ".MOV"]:
                    lang_vid = os.path.join(template_dir, f"{lang_code}{ext}")
                    if os.path.exists(lang_vid):
                        found_vid = lang_vid
                        break
                if found_vid:
                    template_videos[lang_code] = found_vid
    
    # We let the renderer calculate the precise start time using 'Main - Outro'
    precise_outro_start = None

    # Read validated transcription
    with open(transcription_json_path, 'r', encoding='utf-8') as f:
        transcription_data = json.load(f)
    
    raw_segments = transcription_data.get("segments", [])
    
    # Smart Temporal Expansion (using precise outro start as limit)
    def expand_segs(segs, total_dur, outro_limit):
        if not segs: return []
        expanded = []
        limit = outro_limit if outro_limit is not None else total_dur
        for i in range(len(segs)):
            s = segs[i].copy()
            p_end = segs[i-1]['end'] if i > 0 else 0
            n_start = segs[i+1]['start'] if i + 1 < len(segs) else limit
            
            exp_pre = min(0.4, max(0, (s['start'] - p_end) * 0.4))
            exp_post = min(0.4, max(0, (n_start - s['end']) * 0.4))
            s['start'] = round(s['start'] - exp_pre, 3)
            s['end'] = round(s['end'] + exp_post, 3)
            s['duration'] = round(s['end'] - s['start'], 2)
            expanded.append(s)
        return expanded

    expanded_segments = expand_segs(raw_segments, total_video_dur, precise_outro_start)
    
    # Build structured segments for translation
    structured_segments = []
    for s in expanded_segments:
        text = s.get("text", "").strip()
        if text:
            start = s.get("start", 0.0)
            end = s.get("end", 0.0)
            structured_segments.append({
                "full_text": text,
                "start": start,
                "end": end,
                "duration": round(end - start, 2)
            })
    
    results = {}
    errors = []
    
    try:
        # Process languages in parallel
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
            futures = {}
            for lang_code in TARGET_LANGUAGES:
                template_path = template_videos.get(lang_code)
                future = executor.submit(
                    process_single_language,
                    lang_code, job_dir, structured_segments, bgm_path,
                    source_video_path, subtitle_position, video_width, video_height,
                    voice_id, None, template_videos.get(lang_code),
                    subtitle_y_percent, is_overlay
                )
                futures[future] = lang_code
            
            for future in as_completed(futures):
                lang_code = futures[future]
                try:
                    res = future.result()
                    results[lang_code] = res
                    logger.info(f"✅ {lang_code} completed")
                except Exception as e:
                    logger.error(f"❌ {lang_code} failed: {e}")
                    errors.append(f"{lang_code}: {e}")
    finally:
        pass
                
    success_count = sum(1 for r in results.values() if r.get("status") == "DONE")
    return {
        "status": "DONE" if not errors else "PARTIAL",
        "results": results,
        "errors": errors,
        "success_count": success_count,
        "total_count": len(TARGET_LANGUAGES)
    }
