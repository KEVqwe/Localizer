@echo off
CHCP 65001 >nul
TITLE Localizer Worker - Installer
SETLOCAL EnableDelayedExpansion

echo ===========================================
echo   步骤 0: 检查系统环境与依赖...
echo ===========================================
powershell -ExecutionPolicy Bypass -File "%~dp0COLLEAGUE_AUTO_PREP.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 系统环境准备失败，请检查报错。
    pause
    exit /b
)
echo.

:: 1. 检查 Conda
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Conda！
    echo 请先安装 Miniconda: https://docs.anaconda.com/miniconda/
    pause
    exit /b
)

:: 2. 创建环境 (py311)
echo [1/4] 检查/创建 AI 运行环境 (py311)...
CALL conda env list | findstr "py311" >nul
if %ERRORLEVEL% EQU 0 (
    echo [跳过] 'py311' 环境已存在。
) else (
    echo [进度] 正在创建 py311 环境，请稍候...
    CALL conda create -n py311 python=3.11 -y
)
echo.

:: 3. 寻找激活脚本
SET "ACT_PATH="
IF EXIST "%USERPROFILE%\miniconda3\Scripts\activate.bat" SET "ACT_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
IF EXIST "C:\ProgramData\miniconda3\Scripts\activate.bat" SET "ACT_PATH=C:\ProgramData\miniconda3\Scripts\activate.bat"

:: 4. 安装核心依赖
echo [2/4] 安装 AI 核心组件 (Torch / WhisperX)...
if "%ACT_PATH%"=="" (
    CALL conda.bat activate py311
) else (
    CALL "%ACT_PATH%" py311
)

echo [进度] 安装 PyTorch (CUDA 11.8)...
CALL pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
echo [进度] 安装 WhisperX...
CALL pip install git+https://github.com/m-bain/whisperX.git
echo [进度] 安装 谷歌 AI SDK (google-genai)...
CALL pip install google-genai
echo [进度] 安装 其他业务依赖...
CALL pip install celery redis pydub fastapi uvicorn python-dotenv

:: 5. 安装 PM2
echo.
echo [3/4] 安装 进程管理器 (PM2)...
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 未找到 Node.js/npm，将跳过 PM2 安装。
) else (
    CALL npm install -g pm2
)

:: 6. 检查 FFmpeg
echo.
echo [4/4] 检查 多媒体引擎 (FFmpeg)...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 未找到 FFmpeg，请确保安装了 Gyan.FFmpeg 且已重启终端。
)

echo.
echo ==========================================
echo   安装完成！
echo ==========================================
echo 提示：现在可以运行 [START_WORKER.bat] 启动节点。
echo.
pause
