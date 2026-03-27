import os
import requests
import math
import subprocess
from worker.src.utils.logger import setup_logger
from worker.src.utils.ffmpeg_manager import get_media_duration, get_ffmpeg_path

logger = setup_logger(__name__)

logger = setup_logger(__name__)

# Standard High-Quality ElevenLabs Voices Registry
# Mapped to descriptive personas for Gemini-powered smart selection
VOICE_PERSONA_REGISTRY = {
    "male_deep": "D37zOfS367664B95EBD5",      # Finn - Mature, Narrative
    "male_energetic": "29vD33N1HipS3f17QNAs", # Drew - Ads, Energetic
    "female_soft": "21m00Tcm4TlvDq8ikWAM",    # Rachel - Professional, Mature
    "female_young": "pFZP5JQG7iQjIQuC4Bku",   # Lily - Young, High-pitch, Kawaii
}

# Fallbacks
MALE_VOICE_ID = VOICE_PERSONA_REGISTRY["male_energetic"]
FEMALE_VOICE_ID = VOICE_PERSONA_REGISTRY["female_soft"]
DEFAULT_VOICE_ID = FEMALE_VOICE_ID

def generate_tts_elevenlabs(text: str, language_code: str, output_mp3_path: str, voice_id: str = None) -> str:
    """
    Generates realistic voiceover using ElevenLabs API.
    Can utilize a custom cloned voice_id or falls back to standard voice.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    
    if not voice_id:
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
    
    if not api_key:
        logger.warning(f"ELEVENLABS_API_KEY not found. Skipping TTS for {language_code}.")
        with open(output_mp3_path, 'wb') as f:
            pass # Create empty file to prevent pipeline crashes
        return output_mp3_path
        
    logger.info(f"Generating TTS for {language_code}: '{text[:30]}...'")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    # Configurable voice settings via .env (Refined for maximum similarity)
    base_stability = float(os.environ.get("ELEVENLABS_STABILITY", "0.7"))
    similarity_boost = float(os.environ.get("ELEVENLABS_SIMILARITY", "0.9"))
    style = float(os.environ.get("ELEVENLABS_STYLE", "0.0"))
    use_speaker_boost = os.environ.get("ELEVENLABS_SPEAKER_BOOST", "true").lower() == "true"
    
    # Verbose languages (Spanish, German, Portuguese) get an extra stability nudge
    verbose_langs = {"es", "de", "pt"}
    if language_code.lower() in verbose_langs:
        base_stability = min(1.0, base_stability + 0.10)
        logger.info(f"Applied +0.10 stability boost for verbose language '{language_code}' → {base_stability:.2f}")
    
    # ElevenLabs uses its own ISO 639-3 language codes (not standard 2-letter codes)
    # This FORCES correct pronunciation — without it, "mist" in German gets read as English
    ELEVENLABS_LANG_MAP = {
        "de": "de",  "es": "es",  "fr": "fr",
        "id": "id",  "it": "it",  "pl": "pl",
        "pt": "pt",  "ru": "ru",  "tr": "tr",
    }
    el_lang = ELEVENLABS_LANG_MAP.get(language_code.lower())
    if el_lang:
        logger.info(f"Forcing ElevenLabs language: {el_lang}")
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": base_stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        }
    }
    
    # Explicitly set language to prevent misidentification
    if el_lang:
        data["language_code"] = el_lang
    
    try:
        # Added 60s timeout to prevent hanging on flaky API connections
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"TTS Generation Failed! Status: {response.status_code}")
            logger.error(f"Voice ID used: {voice_id}")
            logger.error(f"Error Details: {response.text}")
            response.raise_for_status()
        
        # Directly write raw bytes
        with open(output_mp3_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Successfully generated TTS audio ({len(response.content)} bytes) at {output_mp3_path}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"ElevenLabs HTTP request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error formatting ElevenLabs TTS: {e}")
        raise
        
    return output_mp3_path
