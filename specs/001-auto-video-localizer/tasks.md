---
description: "Task list template for feature implementation"
---

# Tasks: Auto Video Localizer

**Input**: Design documents from `/specs/001-auto-video-localizer/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: As per Constitution Principle II, Test-Driven Development (TDD) or comprehensive unit/integration tests are MANDATORY for all features (especially video/audio pipeline and UI routing). Tests MUST be written for each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Initialize Python project with `fastapi`, `celery`, `redis`, and `pytest` in `server/requirements.txt` and `worker/requirements.txt`
- [x] T002 Initialize Client project (Electron/Tauri) in `client/package.json`
- [x] T003 [P] Configure linting (`ruff`/`black` for Python, `eslint` for Client)
- [x] T004 Setup Docker/Docker-Compose for Redis orchestration in `docker-compose.yml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Create `VideoAsset`, `LocalizationJob`, `Phase1ExtractionTask`, `WorkerNode`, `LocalizedVideo` models in `server/src/models/`
- [x] T006 [P] Setup Celery/Redis connection logic in `server/src/queue/celery_app.py`
- [x] T007 Implement the `free_vram()` strict CUDA cleaner hook in `worker/src/utils/gpu_manager.py`
- [x] T008 Configure FFmpeg path resolving and validation in `worker/src/utils/ffmpeg_manager.py`
- [x] T009 Create unified error handling & logging (especially for CUDA OOM errors) in `worker/src/utils/logger.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - One-Click 9-Language Generation (Priority: P1) 🎯 MVP

**Goal**: Convert a 1-minute English video into 9 completely localized versions.

**Independent Test**: Send a video to the pipeline and verify 9 target MP4s appear with properly swapped audio, subs, and UI.

### Tests for User Story (MANDATORY) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US1] Unit test for VRAM ceiling inside extraction pipeline in `worker/tests/test_gpu_manager.py`
- [x] T011 [P] [US1] Integration test for FFmpeg NVENC muxing in `worker/tests/test_phase3_render.py`

### Implementation for User Story 1

- [x] T012 [P] [US1] Implement Demucs Audio Isolation in `worker/src/phase1_gpu/demucs_extractor.py`
- [x] T013 [P] [US1] Implement WhisperX STT in `worker/src/phase1_gpu/whisper_transcriber.py`
- [x] T014 [P] [US1] Implement Qwen2.5-VL-3B UI Extractor in `worker/src/phase1_gpu/qwen_ui_detector.py`
- [x] T015 [US1] Create the Phase 1 Orchestrator in `worker/src/phase1_gpu/pipeline.py` (depends on T012, T013, T014, and T007 `free_vram`)
- [x] T016 [P] [US1] Implement GPT-4o Translation API wrapper in `worker/src/phase2_api/translator.py`
- [x] T017 [P] [US1] Implement ElevenLabs TTS wrapper in `worker/src/phase2_api/tts_generator.py`
- [x] T018 [US1] Implement FFmpeg Hardware (NVENC) Renderer combining Video, TTS, Subs, and UI in `worker/src/phase3_render/renderer.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Distributed GPU Task Stealing (Priority: P2)

**Goal**: Idle workstations automatically pick up Phase 1 extraction tasks via Redis from busy workstations.

**Independent Test**: Load Redis with a task, ensure a worker running on another IP picks it up and returns the result.

### Tests for User Story (MANDATORY) ⚠️

- [x] T019 [P] [US2] Mock Redis Queue test ensuring tasks are distributed to workers registering as `IDLE` in `server/tests/test_queue.py`

### Implementation for User Story 2

- [x] T020 [P] [US2] Create Node Monitor script to report `IDLE` or `BUSY` status based on active CUDA utilization in `worker/src/monitor.py`
- [x] T021 [US2] Wrap Phase 1 Orchestrator (T015) in a Celery Worker thread in `worker/src/celery_tasks.py`
- [x] T022 [US2] Implement `/api/v1/jobs/submit` and `/api/v1/nodes/status` in `server/src/api/router.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Human-in-the-Loop Validation (Priority: P3)

**Goal**: Pipeline pauses after Phase 1 and waits for user confirmation of English Subtitles and UI JSON before proceeding to Phase 2 (Cost saving).

**Independent Test**: Pipeline status reaches `WAITING_VALIDATION` and halts until `/api/v1/jobs/approve` is hit.

### Tests for User Story (MANDATORY) ⚠️

- [x] T023 [P] [US3] API integration test verifying the pause and resume functionality in `server/tests/test_approval_flow.py`

### Implementation for User Story 3

- [x] T024 [P] [US3] Implement `/api/v1/jobs/approve/{task_id}` logic to transition state to `APPROVED` and trigger Phase 2 in `server/src/api/router.py`
- [x] T025 [P] [US3] Build Desktop client React form for editing Subtitles and UI JSON array in `client/src/review/ValidationForm.tsx`
- [x] T026 [US3] Integrate ValidationForm to hit the Approve API Endpoint upon user submission in `client/src/services/api.ts`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T027 [P] Finalize API error handling and status code bubbling from Worker -> Redis -> Server
- [x] T028 Optimize Docker Compose default arguments for LAN networking
- [x] T029 Write Setup Documentation for adding new Worker Nodes locally (assumes studio colleagues' RTX 4070/4080 machines)
- [x] T030 Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion

### User Story Dependencies

- **User Story 1 (P1)**: The core pipeline processing script. Can proceed independently.
- **User Story 2 (P2)**: Depends on US1 existing to encapsulate it in Celery.
- **User Story 3 (P3)**: Depends on US1 existing to pause its execution loop.

### Parallel Opportunities

- In US1, the API wrappers (`translator.py` and `tts_generator.py`) and standard GPU pipelines (`whisper_transcriber.py`, `qwen_ui_detector.py`) can be built in completely separate PRs simultaneously.
- Client validation form (US3) can be built in parallel while Server logic is being structured.
