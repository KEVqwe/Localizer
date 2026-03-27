---
description: "功能实现任务列表模板"
---

# 任务：自动视频本地化工具 (Auto Video Localizer)

**输入**：来自 `/specs/001-auto-video-localizer/` 的设计文档
**前置条件**：plan.md (必填), spec.md (用户故事必填), research.md, data-model.md, contracts/

**测试**：根据宪章原则 II，测试驱动开发 (TDD) 或全面的单元/集成测试对于所有功能（特别是视频/音频管道和 UI 路由）是**强制的**。必须为每个用户故事编写测试。

**组织结构**：任务按用户故事分组，以便每个故事能独立实现和测试。

## 格式：`[ID] [P?] [Story] 描述`

- **[P]**：可以并行执行（不同的文件，没有依赖关系）
- **[Story]**：该任务属于哪个用户故事（例如，US1, US2, US3）
- 在描述中包含准确的文件路径

## 阶段 1：构建设置 (共享基础设施)

**目的**：项目初始化和基本结构

- [ ] T001 初始化 Python 项目，在 `server/requirements.txt` 和 `worker/requirements.txt` 中添加 `fastapi`, `celery`, `redis` 和 `pytest`
- [ ] T002 在 `client/package.json` 中初始化客户端项目 (Electron/Tauri)
- [ ] T003 [P] 配置代码规范检查工具（Python 使用 `ruff`/`black`，客户端使用 `eslint`）
- [ ] T004 在 `docker-compose.yml` 中设置 Docker/Docker-Compose 以进行 Redis 编排

---

## 阶段 2：基础建设 (阻塞性前置条件)

**目的**：在实现任何用户故事之前**必须**完成的核心基础设施

**⚠️ 关键**：在此阶段完成之前，不得开始任何用户故事的开发

- [ ] T005 [P] 在 `server/src/models/` 中创建 `VideoAsset`, `LocalizationJob`, `Phase1ExtractionTask`, `WorkerNode`, `LocalizedVideo` 模型
- [ ] T006 [P] 在 `server/src/queue/celery_app.py` 中设置 Celery/Redis 连接逻辑
- [ ] T007 在 `worker/src/utils/gpu_manager.py` 中实现 `free_vram()` 严格的 CUDA 清理钩子
- [ ] T008 在 `worker/src/utils/ffmpeg_manager.py` 中配置 FFmpeg 路径解析和验证
- [ ] T009 在 `worker/src/utils/logger.py` 中创建统一的错误处理和日志记录（特别是对于 CUDA OOM 错误）

**检查点**：基础建设已准备就绪 - 现在可以并行开始实现用户故事

---

## 阶段 3：用户故事 1 - 一键生成 9 种语言 (优先级: P1) 🎯 MVP

**目标**：将一个 1 分钟的英语视频转换为 9 个完全本地化的版本。

**独立测试**：将一个视频发送到处理管道，并验证是否生成了 9 个目标 MP4 文件，且音频、字幕和 UI 都已正确替换。

### 用户故事的测试 (强制) ⚠️

> **注意：首先编写这些测试，确保在实现之前它们会失败**

- [ ] T010 [P] [US1] 在 `worker/tests/test_gpu_manager.py` 中为提取管道内部的 VRAM 上限编写单元测试
- [ ] T011 [P] [US1] 在 `worker/tests/test_phase3_render.py` 中为 FFmpeg NVENC 混合编写集成测试

### 用户故事 1 的实现

- [ ] T012 [P] [US1] 在 `worker/src/phase1_gpu/demucs_extractor.py` 中实现 Demucs 音频分离
- [ ] T013 [P] [US1] 在 `worker/src/phase1_gpu/whisper_transcriber.py` 中实现 WhisperX 语音转文本 (STT)
- [ ] T014 [P] [US1] 在 `worker/src/phase1_gpu/qwen_ui_detector.py` 中实现 Qwen2.5-VL-3B UI 提取器
- [ ] T015 [US1] 在 `worker/src/phase1_gpu/pipeline.py` 中创建阶段 1 编排器（依赖于 T012, T013, T014 以及 T007 的 `free_vram`）
- [ ] T016 [P] [US1] 在 `worker/src/phase2_api/translator.py` 中实现 GPT-4o 翻译 API 包装器
- [ ] T017 [P] [US1] 在 `worker/src/phase2_api/tts_generator.py` 中实现 ElevenLabs TTS 包装器
- [ ] T018 [US1] 在 `worker/src/phase3_render/renderer.py` 中实现结合视频、TTS、字幕和 UI 的 FFmpeg 硬件（NVENC）渲染器

**检查点**：此时，用户故事 1 应该功能完全独立可用且可独立测试

---

## 阶段 4：用户故事 2 - 分布式 GPU 任务窃取 (优先级: P2)

**目标**：空闲工作站通过 Redis 自动从繁忙工作站接手阶段 1 的提取任务。

**独立测试**：向 Redis 中加载一个任务，确保在另一个 IP 上运行的工作节点能接手它并返回结果。

### 用户故事的测试 (强制) ⚠️

- [ ] T019 [P] [US2] 在 `server/tests/test_queue.py` 中编写模拟 Redis 队列测试，确保任务被分发到注册为 `IDLE`（空闲）的工作节点

### 用户故事 2 的实现

- [ ] T020 [P] [US2] 在 `worker/src/monitor.py` 中创建节点监控脚本，根据活动的 CUDA 使用率报告 `IDLE` 或 `BUSY` 状态
- [ ] T021 [US2] 在 `worker/src/celery_tasks.py` 中将阶段 1 编排器 (T015) 封装到 Celery Worker 线程中
- [ ] T022 [US2] 在 `server/src/api/router.py` 中实现 `/api/v1/jobs/submit` 和 `/api/v1/nodes/status` 接口

**检查点**：此时，用户故事 1 和 2 应该都能独立工作

---

## 阶段 5：用户故事 3 - 让人参与验证 (Human-in-the-Loop) (优先级: P3)

**目标**：阶段 1 完成后管道暂停，等待用户确认英语字幕和 UI JSON 之后再进入阶段 2（节省成本）。

**独立测试**：管道状态达到 `WAITING_VALIDATION` 并暂停，直到 `/api/v1/jobs/approve` 被调用。

### 用户故事的测试 (强制) ⚠️

- [ ] T023 [P] [US3] 在 `server/tests/test_approval_flow.py` 中编写 API 集成测试，验证暂停和恢复功能

### 用户故事 3 的实现

- [ ] T024 [P] [US3] 在 `server/src/api/router.py` 中实现 `/api/v1/jobs/approve/{task_id}` 逻辑，将状态转换为 `APPROVED` 并触发阶段 2
- [ ] T025 [P] [US3] 在 `client/src/review/ValidationForm.tsx` 中构建用于编辑字幕和 UI JSON 数组的桌面客户端 React 表单
- [ ] T026 [US3] 在 `client/src/services/api.ts` 中集成 ValidationForm，在用户提交时调用 Approve API 接口

**检查点**：所有用户故事现在都应该能独立运行

---

## 阶段 6：打磨和跨领域关注点

**目的**：影响多个用户故事的改进

- [ ] T027 [P] 完善从 Worker -> Redis -> Server 的 API 错误处理和状态码冒泡机制
- [ ] T028 优化 LAN 网络的 Docker Compose 默认参数
- [ ] T029 编写在本地添加新工作节点的设置文档（针对工作室同事的 RTX 4070/4080 电脑）
- [ ] T030 运行 quickstart.md 验证

---

## 依赖关系和执行顺序

### 阶段依赖

- **构建设置 (阶段 1)**：无依赖 - 可以立即开始
- **基础建设 (阶段 2)**：取决于设置完成 - **阻塞**所有用户故事
- **用户故事 (阶段 3+)**：都取决于基础建设阶段的完成

### 用户故事依赖

- **用户故事 1 (P1)**：核心管道处理脚本。可以独立进行。
- **用户故事 2 (P2)**：依赖 US1 的存在以便将其封装在 Celery 中。
- **用户故事 3 (P3)**：依赖 US1 的存在以便可以暂停其执行循环。

### 并行机会

- 在 US1 中，API 包装器（`translator.py` 和 `tts_generator.py`）以及标准的 GPU 管道（`whisper_transcriber.py`, `qwen_ui_detector.py`）可以在完全独立的 PR 中同时构建。
- 客户端验证表单 (US3) 可以在服务器逻辑构建的同时并行开发。
