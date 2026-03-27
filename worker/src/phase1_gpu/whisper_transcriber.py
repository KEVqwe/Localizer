import json
from worker.src.utils.gpu_manager import logger, free_vram

try:
    import whisperx
except ImportError:
    whisperx = None

def transcribe_audio(audio_path: str, output_json_path: str):
    """
    Transcribes audio using WhisperX and saves word-level timestamp JSON.
    """
    logger.info(f"Running WhisperX on {audio_path}")
    if whisperx is None:
        logger.warning("WhisperX not installed. Mocking transcription.")
        result = {"segments": [{"text": "Mock transcription", "start": 0.0, "end": 1.0}]}
    else:
        model = whisperx.load_model("large-v3", "cuda", compute_type="float16")
        audio = whisperx.load_audio(audio_path)
        # Force language=en to skip detection and speed up Phase 1
        logger.info("[DEBUG] Calling model.transcribe with language='en'...")
        result = model.transcribe(audio, batch_size=16, language="en")
        
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device="cuda")
        result = whisperx.align(result["segments"], model_a, metadata, audio, "cuda", return_char_alignments=False)
        
        del model
        del model_a
        free_vram()
        
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        
    return output_json_path
