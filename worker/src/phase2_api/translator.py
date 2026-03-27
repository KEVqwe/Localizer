import os
import json
from google import genai
from google.genai import types
from worker.src.utils.logger import setup_logger

logger = setup_logger(__name__)

def translate_content(transcription_json: list, target_language: str) -> dict:
    """
    Orchestrates translation using Google Gemini 2.0 Flash.
    """
    return _translate_with_gemini(transcription_json, target_language)


def _translate_with_gemini(transcription_json: list, target_language: str) -> dict:
    """Uses Gemini 3 Flash Preview for translation."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
        
    client = genai.Client(api_key=api_key)
    
    payload = {"transcription": transcription_json}
    
    instruction = f"""
    You are an expert video localization translator.
    You will receive a JSON array where each object has 'full_text', 'start', 'end', and 'duration' (max seconds available).
    1. Translate the 'full_text' of each item into {target_language}.
    2. Split the translated text into natural, easy-to-read subtitle 'chunks'.
    
    CRITICAL TONE AND STYLE GUIDELINES:
    - The translation MUST BE highly natural, colloquial, and conversational.
    - Absolutely NO formal, stiff, or written-style ("textbook") language.
    - The context is a high-energy ADVERTISEMENT promoting and introducing on-screen content. Use an engaging, energetic, and persuasive marketing tone (like a gaming streamer or announcer).
    
    DUBBING AND TIMING CONSTRAINTS (CRITICAL):
    - You must achieve "Timing Parity". Each segment's translation must fit naturally within its specified `duration`.
    - If a literal translation is too long to speak at a moderate, expressive pace, you MUST apply "Condensation" (缩译).
    - Use shorter, punchy synonyms and remove filler words to ensure the sentence is compact.
    - Prioritize timing and natural flow over 1:1 literal meaning, provided the core marketing message remains.
    
    CRITICAL CHUNKING RULES:
    - If the translated sentence is 30 characters or fewer (including spaces), DO NOT split it. Return it as a SINGLE chunk.
    - Only split into multiple chunks if the sentence is long (exceeds 30 characters).
    - NEVER create a chunk with only 1 word or a stray punctuation mark. Group them with adjacent text.
    
    Output JSON array format MUST STRICTLY BE:
    [
      {{
        "full_text": "<complete translated sentence>",
        "start": <original start timestamp>,
        "end": <original end timestamp>,
        "chunks": [ "<sub-chunk 1>" ]
      }}
    ]
    Maintain the EXACT order and the original start/end timestamps from the input!
    """

    # Language-specific specialization
    instruction += """
    DUBBING PRECISION (CRITICAL):
    - Avoid including interjections, filler words, or hesitation sounds (like "¡Hmm...", "¡Oh...", "¡Shhh!", "¡Ugh!") in the translation. 
    - These sounds can trigger the TTS to speak much slower than the target duration.
    - If the original text contains an interjection, translate only the core meaning or replace it with a meaningful, concise word.
    """

    if target_language.lower() in ["es", "spanish", "西语", "西班牙语"]:
        instruction += """
        SPANISH (es) STYLE:
        - Spanish tends to expand. You MUST be concise and punchy.
        - Prioritize direct, high-energy marketing language.
        - Do not include any filler words or pauses.
        """

    # Try preferred models
    for model_name in ["gemini-3-flash-preview"]:
        try:
            logger.info(f"Semantically Translating & Chunking to {target_language} using {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=json.dumps(payload),
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.warning(f"Translation with {model_name} failed: {e}")
            continue
            
    raise Exception("All translation models failed.")
