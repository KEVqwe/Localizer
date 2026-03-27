# Implementation Plan: Auto Video Localizer (LAN GPU Version)

**Branch**: `001-auto-video-localizer` | **Date**: 2026-03-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-auto-video-localizer/spec.md`

## Summary

The Auto Video Localizer converts a 1-minute English video into 9 languages (DE, ES, FR, ID, IT, PL, PT, RU, TR) simultaneously. The architecture has been rebuilt into a **purely local, distributed LAN architecture**. A 4080 internal workstation operates as the Server (FastAPI + Redis), scheduling tasks. Other 4070 workstations operate as Worker nodes. 

To maximize throughput and prevent OOM errors on 12GB VRAM cards, the job strictly separates VRAM-heavy serialization (Phase 1) from CPU/Network-heavy concurrent compilation (Phase 2) and NVENC hardware rendering (Phase 3). 

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI (Server), Celery/Redis (Task Queue), FFmpeg (Audio/Video), Demucs v4 (Audio Extract), WhisperX (STT), GPT-4o/Claude 3.5 (Translation API), ElevenLabs (TTS API)  
**Testing**: pytest  
**Target Platform**: Desktop Workstation cluster (Internal Studio Gigabit LAN, RTX 4070/4080 nodes)  
**Project Type**: Distributed Client-Server Desktop Application (Python + Electron/Tauri frontend)
**Performance Goals**: <5 minutes turnaround for 1-minute video in 9 languages  
**Constraints**: Deep structural constraint on VRAM (Must not exceed 12GB to support the studio's baseline RTX 4070/4080 hardware). Zero-cost cloud GPU assumption (runs entirely on local LAN for heavy lifting). 
**Scale/Scope**: 9 target languages.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Code Quality**: Architecture strictly separates Phase 1 (GPU logic), Phase 2 (CPU/API logic), and Phase 3 (NVENC mixing).
- [x] **Testing Standards**: Test coverage documented for subtitle parsing, dubbing sync, and UI translation logic. PRs cannot merge without test plans.
- [x] **UX Consistency**: 1-click English -> 9 languages is preserved, but with an intermediate validation checkpoint to prevent API transcription errors.
- [x] **Performance**: VRAM is aggressively managed via `free_vram()` between Demucs and WhisperX to prevent OOM on 12GB cards. UI element detection (Qwen2.5-VL) deferred to future milestone.

## Project Structure

### Documentation (this feature)

```text
specs/001-auto-video-localizer/
├── plan.md              # This file
├── research.md          # 
├── data-model.md        # 
├── quickstart.md        # 
├── contracts/           # API mappings
└── tasks.md             # 
```

### Source Code (repository root)

```text
server/                  # FastAPI + Redis Orchestrator
├── src/
│   ├── api/
│   └── queue/           # Redis broker definitions

worker/                  # GPU / CPU Worker Node Code
├── src/
│   ├── phase1_gpu/      # Demucs, WhisperX (UI detection deferred)
│   ├── phase2_api/      # OpenAI, ElevenLabs handlers
│   └── phase3_render/   # FFmpeg NVENC logic

client/                  # User Interface (Desktop Shell / Web UI)
├── src/
│   ├── upload/
│   ├── review/          # Human-in-the-loop form
│   └── monitor/         # Cluster node status
```

**Structure Decision**: Option 4: Distributed System. Split into Server (Orchestrator), Worker (Execution), and Client (UI/Validation).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Local LAN Cluster vs Cloud | Deep privacy, 0$ operational cost past hardware, User strictly demanded "Local Geek Workstation Distributed Architecture". | Cloud Kubernetes cluster rejected due to high GPU instance costs. |
| Splitting Phases + Redis | A single Python script will OOM a 12GB RTX 4070 when trying to compile 9 languages after running Qwen. | Simple sequential loop rejected because the computer would freeze and become unusable for developers. Task stealing via Redis is mandatory. |
| Human in the loop pause | The user mandates that developers must check the Whisper/OCR output before triggering the 9-language translation APIs | Fully automated pipeline rejected to save substantial API credit waste from poorly interpreted source videos. |
