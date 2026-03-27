# Feature Specification: Automated Multi-Language Video Localizer (LAN Distributed GPU Version)

**Feature Branch**: `001-auto-video-localizer`  
**Created**: 2026-03-11  
**Status**: Draft  
**Input**: User description: "一个自动化多语言本地化工具。用户场景：平均1分钟的短视频..." + "自动化多语种视频本地化系统 - 本地算力架构设计与落地方案 (局域网版)"

## Target Audience & Operational Environment

- **Target Audience**: Internal studio colleagues (video editors, content creators). Not a public SaaS.
- **Hardware Baseline**: Every user has a high-end workstation equipped with an Nvidia RTX 4070 or 4080 (12GB - 16GB VRAM).
- **Network Environment**: High-speed internal Gigabit LAN.
- **Primary Driver**: Zero marginal cost for processing video (bypassing cloud GPU rent), extreme data privacy for unreleased commercial content, and maximizing the utilization of idle team hardware.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Click 9-Language Generation (Priority: P1)

Users upload a single 1-minute English video and automatically receive 9 fully localized versions (DE, ES, FR, ID, IT, PL, PT, RU, TR).

**Why this priority**: Core value proposition.

**Independent Test**: Upload a sample 1-minute English video. Verify 9 distinct MP4s are produced.

**Acceptance Scenarios**:

1. **Given** a 1-minute English video, **When** uploaded, **Then** 9 new videos are generated for the 9 target languages.

---

### User Story 2 - Distributed GPU Task Stealing (Priority: P2)

When a user's local RTX 4070/4080 is busy (e.g., playing a game), the localization job is sent to a central Redis queue, and another idle workstation on the LAN picks up the VRAM-intensive Phase 1 tasks.

**Why this priority**: Ensures system doesn't crash busy developer machines while maximizing team hardware ROI.

**Independent Test**: Simulate high GPU load on Client A, submit a job. Verify Client B (idle) picks up the extraction task via Redis.

**Acceptance Scenarios**:

1. **Given** Client A is busy and Client B is idle, **When** Client A submits a video, **Then** Client B executes the GPU extraction and returns the JSON payload.

---

### User Story 3 - Human-in-the-Loop Validation (Priority: P3)

Before spending expensive API credits on the 9-language generation (Phase 2), the system pauses and presents a UI for the user to manually validate/fix the extracted English SRT and UI bounding boxes.

**Why this priority**: Prevents garbage-in-garbage-out and saves API costs.

**Independent Test**: Upload a video. Verify the pipeline pauses after Phase 1, waiting for user approval via a web UI before proceeding.

**Acceptance Scenarios**:

1. **Given** a completed Phase 1 extraction, **When** the payload is ready, **Then** the UI prompts for human review before continuing.

## Constitution Compliance *(mandatory)*

- **Code Quality**: Architecture strictly separates Phase 1 (GPU logic), Phase 2 (CPU/API logic), and Phase 3 (NVENC mixing).
- **UX Consistency**: 1-click English -> 9 languages is preserved, but with an intermediate validation checkpoint to prevent API transcription errors.
- **Performance**: VRAM is aggressively managed via `free_vram()` between Demucs and WhisperX to prevent OOM on 12GB cards.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST process tasks in 3 distinct phases: GPU Extraction (Phase 1), API/CPU Generation (Phase 2), and NVENC Rendering (Phase 3).
- **FR-002**: System MUST enforce VRAM cleanup between models (Demucs -> WhisperX) during Phase 1. UI element detection is deferred to a future milestone.
- **FR-003**: System MUST pause after Phase 1 for human validation (Human-in-the-Loop).
- **FR-004**: System MUST use GPT-4o/Claude 3.5 for 9-language translation and ElevenLabs for TTS (Phase 2).
- **FR-005**: System MUST perform final video rendering utilizing FFmpeg's hardware acceleration (`h264_nvenc` / `hevc_nvenc`) (Phase 3).
- **FR-006**: System MUST support a Server-Worker LAN topology via Redis for task distribution, assuming a homogeneous cluster of RTX 4070/4080 nodes.

### Key Entities

- **VideoAsset**: Represents the uploaded video.
- **LocalizationJob**: Tracks the state across Phase 1, Human Validation, and Phases 2-3.
- **WorkerNode**: Represents a workstation on the LAN (idle or busy).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System does not exceed 10GB VRAM peak usage during Phase 1.
- **SC-002**: 9 target languages successfully generated without VRAM OOM exceptions.
- **SC-003**: Final MP4 rendering (Phase 3) utilizes NVENC encoding, observable via GPU engine utilization.
