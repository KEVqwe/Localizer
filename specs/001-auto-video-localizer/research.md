# Research: Auto Video Localizer (LAN GPU Edition)

## Technical Context Decisions

### Decision 1: Language & Architecture Style
- **Decision**: Python (FastAPI Server + Celery/Redis Workers) + Electron/Tauri (Client Desktop App).
- **Rationale**: 
  - **Context**: Designed for internal studio colleagues where every machine is an RTX 4070/4080.
  - **Server (1 machine)**: Central API gateway and Redis broker to govern the queue.
  - **Worker**: Every workstation acts as a worker. Tasks are pulled from Redis. If the local machine is idle, it takes its own tasks. If busy, it offloads to the LAN. This achieves "zero marginal cost" by utilizing already-paid-for hardware.
- **Alternatives considered**: Kubernetes/Cloud API (rejected: expensive cloud GPU rent, violates strict internal data privacy needs for unreleased content).

### Decision 2: AI Models for Phase 1 (GPU Extraction)
- **Decision**: 
  - Audio Isolation: Demucs v4
  - Transcription (STT): WhisperX (large-v3) for word-level timestamps.
  - Visual UI Detection: Qwen2.5-VL-3B-Instruct (FP16).
- **Rationale**: 
  - Strict VRAM limits (12GB - 16GB). These models must run in *serial*. 
  - Qwen2.5-VL-3B replaces the original 7B to guarantee it fits entirely inside 7GB VRAM, preventing OOM crashes on RTX 4070s.
- **Alternatives considered**: Qwen-VL-Max (rejected: too large for 12GB).

### Decision 3: Translation and TTS (Phase 2)
- **Decision**: GPT-4o / Claude 3.5 (Translation) and ElevenLabs (TTS).
- **Rationale**: 9-language concurrent generation requires deep colloquial understanding and precise JSON length control. Local LLMs (7B class) frequently break JSON structure. High-quality multi-lingual tone matching currently requires ElevenLabs.
- **Alternatives considered**: Local XTTSv2 (rejected: quality compromise, saved as a fallback).

### Decision 4: Video Processing (Phase 3)
- **Decision**: FFmpeg with `h264_nvenc` hardware acceleration.
- **Rationale**: Using the dedicated NVENC silicon on the RTX 40 series skips standard CUDA cores and processes massive 9-video multiplexing up to 10x faster than CPU without competing for VRAM.

### Decision 5: VRAM Management Core
- **Decision**: Explicit `free_vram()` hook.
- **Rationale**: `torch.cuda.empty_cache()` and `gc.collect()` must be forcefully executed after each model's inference in Phase 1.
