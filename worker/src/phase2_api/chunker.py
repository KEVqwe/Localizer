import json
import re
import os

def chunk_segment(segment: dict, words: list, max_words=6) -> list:
    """
    Splits a long segment into smaller chunks based on punctuation and word count,
    using word-level timestamps to determine the start/end of each chunk.
    """
    chunks = []
    current_chunk_words = []
    current_text = ""
    
    for word_info in words:
        word = word_info["word"].strip()
        current_chunk_words.append(word_info)
        current_text += (" " + word if current_text else word)
        
        has_punctuation = bool(re.search(r'[.,!?]', word))
        is_too_long = len(current_chunk_words) >= max_words
        
        # Don't split if the chunk is just 1 word, even if it has punctuation 
        # (unless it's forced by is_too_long, which implies max_words=1 but default is 6)
        should_split = (has_punctuation and len(current_chunk_words) >= 2) or is_too_long
        
        if should_split:
            chunks.append({
                "text": current_text,
                "start": current_chunk_words[0]["start"],
                "end": current_chunk_words[-1]["end"]
            })
            current_chunk_words = []
            current_text = ""
            
    if current_chunk_words:
        chunks.append({
            "text": current_text,
            "start": current_chunk_words[0]["start"],
            "end": current_chunk_words[-1]["end"]
        })
        
    return chunks

def align_and_chunk_validated_subtitles(validated_segments: list, original_transcription_path: str) -> list:
    """
    Aligns user-validated subtitles with original word timestamps, chunks them,
    and formats them for translation and TTS.
    """
    # 1. Load Whisper audio timestamps
    try:
        with open(original_transcription_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"Warning: Could not open {original_transcription_path}, cannot chunk. Error: {e}")
        return [{"full_text": seg["text"], "chunks": [seg]} for seg in validated_segments]

    original_words = []
    if "word_segments" in original_data:
        original_words = original_data["word_segments"]
    else:
        for seg in original_data.get("segments", []):
            original_words.extend(seg.get("words", []))
            
    if not original_words:
        return [{"full_text": seg["text"], "chunks": [seg]} for seg in validated_segments]

    structured_results = []
    
    for val_seg in validated_segments:
        seg_start = val_seg["start"]
        seg_end = val_seg["end"] + 0.5 
        
        matching_words = [
            w for w in original_words 
            if w["start"] >= seg_start - 0.5 and w["end"] <= seg_end
        ]
        
        if not matching_words:
            structured_results.append({"full_text": val_seg["text"], "chunks": [val_seg]})
            continue
            
        # Audio chunks exactly timed for TTS
        chunks = chunk_segment(val_seg, matching_words)
        
        if chunks:
            chunks[0]["start"] = val_seg["start"]
            chunks[-1]["end"] = val_seg["end"]
            
        structured_results.append({
            "full_text": val_seg["text"],
            "chunks": chunks
        })
        
    return structured_results
