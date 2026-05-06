# Localizer: AI-Powered Multi-Language Video Localization Engine 🎬🌍

一个基于多模态 AI（Gemini + WhisperX + ElevenLabs）构建的高精度视频本地化流水线。本项目旨在将原始视频自动转化为多语言版本，支持智能音色匹配、分镜级字幕对齐以及工业级的落版（Outro）物理替换。

依托于 **gemini-3-flash-preview** 的音频分析能力与 **whisperX** 的单词级强制对齐技术，本工具实现了传统自动化配音工具难以企及的“神韵同步”与“视觉无痕”体验。

---

## 🌟 核心引擎与工作流 (The Pipeline)

Localizer 的设计遵循一个严密的分布式 3 阶段流水线：

### 1. 深度提取阶段 (Phase 1: Extraction)
- **声源分离 (Demucs)**：自动将视频音轨分离为背景音乐 (BGM) 与干声人声 (Vocals)。
- **高精度转录 (WhisperX)**：指派 WhisperX 对干声进行转录，提取包含时间戳的原始文本。

### 2. 智能本地化阶段 (Phase 2: Localization)
- **语义分块与翻译 (Gemini API)**：利用 LLM 将长段落智能切分为适合字幕显示的短句，并注入语境进行自然翻译。
- **人设级音色映射 (Persona-Based Voice Mapping)**：
    - **Gemini 声音分析**：自动听取原片，分析说话人的音高、语气与能量级别。
    - **四大预设人设**：自动匹配至最贴合的专业音色（深沉男声、活力男声、知性女声、元气女声），告别生硬的机器人配音。
- **单词级强制对齐 (Word-Level Alignment)**：生成 ElevenLabs 配音后，再次调用 WhisperX 监听生成的音频，确保每一行字幕、每一个单词都与语音节拍精确重合（误差 < 10ms）。

### 3. 后期渲染阶段 (Phase 3: Rendering)
- **视觉擦除 (Subtitle Inpainting)**：根据原片字幕位置，自动进行画面修补，实现字幕区域的“视觉无痕”清理。
- **高阶字幕烧录 (ASS Styling)**：支持动态位置调整、字体特效与阴影，打造院线级视觉质感。
- **物理落版替换 (Outro Splicing/Overlay)**：
    - **倒序对齐算法 (Backwards Alignment)**：自动计算落版时长，实现与原视频结尾的帧级对齐。
    - **多模式支持**：支持透明 Alpha 通道叠加 (Overlay) 或 物理硬切替换 (Replace)。
- **专业混音**：支持 BGM 与 TTS 音量的独立常量控制，确保配音清晰且悦耳。

---

## 🚀 部署与使用 (本地运行)

### 1. 环境准备
确保你的本地安装有 Python (推荐 3.10+ 版本) 以及 FFmpeg。建议使用 Conda 环境。

```bash
# 克隆仓库
git clone https://github.com/your-repo/Localizer.git
cd Localizer

# 安装 Python 依赖
pip install -r worker/requirements.txt
```

### 2. 配置环境变量 (.env)
在项目根目录新建 `.env` 文件，填入必要的 API 密钥：

```env
# AI 核心密钥
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# 渲染控制
TTS_VOLUME=2.0
BGM_VOLUME=1.0
MAX_PARALLEL=5
```

### 3. 启动服务
本项目采用前后端分离架构，配合 Celery 任务队列：

```bash
# 0. 激活 Conda 环境
conda activate py311

# 1. 启动 Redis (任务调度核心)
docker-compose up -d

# 2. 启动 Worker (GPU 算力中心)
celery -A worker.src.celery_tasks worker --loglevel=info -P solo

# 3. 启动 Server (后端 API，端口 8080)
python -m server.src.main

# 4. 启动 Client (前端 Dashboard，端口 5173)
cd client && npm run dev
```

---

## 🛠️ 架构优势 (Enterprise-Grade Stability)

- **并发死锁保护 (ALIGN_LOCK)**：针对 GPU 多线程模型加载进行了物理锁定，即使开启 9 个并发，系统依然能稳健运行，杜绝 CUDA 崩溃。
- **动态超时机制**：所有外部 API 调用均内置 60 秒强制超时，防止网络波动导致的任务卡死。
- **帧级时间间隙 (0.07s Gap)**：在所有相邻字幕块之间强制留出 2 帧空白间隔，彻底消除字幕烧录时的闪烁与重叠问题。
- **全自动清理**：任务完成后自动清理语音克隆配置与临时文件，保护 API 账号配额。

---

## 📝 声明与拓展
- 本工具专为高性能素材制作设计，推荐搭配 RTX 3060 或更高规格显卡使用。
- 严禁用于生成非法内容。
- 基于 ElevenLabs 顶级音色库，结合 Gemini 2.5 Flash 的强劲多模态理解能力，为您提供行业领先的视频本地化体验。
