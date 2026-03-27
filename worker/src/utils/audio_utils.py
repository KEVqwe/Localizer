import os
from pydub import AudioSegment
from worker.src.utils.logger import setup_logger
from worker.src.utils.ffmpeg_manager import get_ffmpeg_path

try:
    import whisperx
    import torch
except ImportError:
    whisperx = None

logger = setup_logger(__name__)

import threading

# Global cache & lock for WhisperX alignment models to prevent parallel GPU deadlocks/OOM
ALIGN_MODEL_CACHE = {}
ALIGN_LOCK = threading.Lock()

def get_align_model(lang_code: str):
    """Retrieves or loads a WhisperX alignment model for the given language (Thread-Safe)."""
    if whisperx is None: return None, None
    
    with ALIGN_LOCK:
        if lang_code in ALIGN_MODEL_CACHE:
            return ALIGN_MODEL_CACHE[lang_code]
        
        logger.info(f"Loading WhisperX align model for language: {lang_code}")
        try:
            model_a, metadata = whisperx.load_align_model(language_code=lang_code, device="cuda")
            ALIGN_MODEL_CACHE[lang_code] = (model_a, metadata)
            return model_a, metadata
        except Exception as e:
            logger.error(f"Failed to load alignment model for {lang_code}: {e}")
            return None, None

def mix_tts_audio(items: list, output_path: str, total_duration_ms: int, voice_id: str = None, language_code: str = "en"):
    """
    Overlays TTS chunks onto a silent track at specified timestamps.
    `items` should be a list of dicts with 'full_text' and 'chunks' (containing 'start').
    """
    # Ensure PyDub uses our resolved FFmpeg
    AudioSegment.converter = get_ffmpeg_path()
    
    final_audio = AudioSegment.silent(duration=total_duration_ms)
    
    from worker.src.phase2_api.tts_generator import generate_tts_elevenlabs
    
    lang_dir = os.path.dirname(output_path)
    
    # Pre-calculate boundary constraints
    for i in range(len(items)):
        if "chunks" not in items[i] or not items[i]["chunks"]:
            items[i]["_start_ms"] = 0
            items[i]["_max_ms"] = total_duration_ms
            continue
            
        start_time_ms = int(items[i]["chunks"][0]["start"] * 1000)
        
        if i + 1 < len(items) and "chunks" in items[i+1] and items[i+1]["chunks"]:
            next_start_ms = int(items[i+1]["chunks"][0]["start"] * 1000)
            max_allowed_ms = next_start_ms - start_time_ms
        else:
            max_allowed_ms = total_duration_ms - start_time_ms
            
        items[i]["_start_ms"] = start_time_ms
        items[i]["_max_ms"] = max_allowed_ms
    
    for item in items:
        full_text = item.get("full_text", "")
        if not full_text.strip():
            continue
            
        sentence_start_ms = int(item["start"] * 1000) if "start" in item else 0
        tmp_tts_path = os.path.join(lang_dir, f"temp_tts_{sentence_start_ms}.mp3")
            
        try:
            # 1. Generate ElevenLabs Audio
            generate_tts_elevenlabs(full_text, language_code, tmp_tts_path, voice_id=voice_id)
            seg_audio = AudioSegment.from_mp3(tmp_tts_path)
            actual_dur_ms = len(seg_audio)
            
            # 2. AI Word-Level Alignment (WhisperX)
            # This 'listens' to the audio to find exactly when words are spoken
            model_a, metadata = get_align_model(language_code)
            if model_a and metadata:
                try:
                    audio_data = whisperx.load_audio(tmp_tts_path)
                    # We pass the full_text as the only segment to align
                    with ALIGN_LOCK:
                        align_result = whisperx.align(
                            [{"text": full_text, "start": 0.0, "end": actual_dur_ms/1000.0}], 
                            model_a, metadata, audio_data, "cuda", return_char_alignments=False
                        )
                    
                    if align_result and align_result["segments"]:
                        words = align_result["segments"][0].get("words", [])
                        
                        # Re-group words into the original chunks
                        chunks = item.get("chunks", [])
                        total_word_idx = 0
                        for c in chunks:
                            chunk_text = c.get("text", "")
                            chunk_word_count = len(chunk_text.split())
                            
                            relevant_words = words[total_word_idx : total_word_idx + chunk_word_count]
                            if relevant_words:
                                # Update global timestamps based on alignment
                                c["start"] = round(item["start"] + relevant_words[0]["start"], 3)
                                c["end"] = round(item["start"] + relevant_words[-1]["end"], 3)
                            
                            total_word_idx += chunk_word_count
                except Exception as align_err:
                    logger.warning(f"WhisperX alignment failed for sentence, falling back to linear: {align_err}")
            
            # 3. Mixing
            from pydub.effects import normalize
            seg_audio = normalize(seg_audio)
            
            max_allowed_ms = item.get("_max_ms", actual_dur_ms)
            if max_allowed_ms > 0 and actual_dur_ms > max_allowed_ms:
                logger.warning(f"TTS too long ({actual_dur_ms}ms > {max_allowed_ms}ms). Hard trimming.")
                seg_audio = seg_audio[:max_allowed_ms]
            
            final_audio = final_audio.overlay(seg_audio, position=sentence_start_ms)
            
        except Exception as e:
            logger.error(f"Failed TTS for sentence '{full_text}': {e}")
        finally:
            if os.path.exists(tmp_tts_path):
                os.remove(tmp_tts_path)
                
    final_audio.export(output_path, format="mp3")
    return output_path
