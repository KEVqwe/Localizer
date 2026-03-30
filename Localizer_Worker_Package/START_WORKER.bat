@echo off
CHCP 65001 >nul
TITLE Localizer Worker - Start Service
SETLOCAL EnableDelayedExpansion

cd /d "%~dp0"

echo ===========================================
echo   步骤 1: 检查配置文件 (.env)
echo ===========================================

:: 如果不存在 .env，或者用户想重置
if not exist .env (
    if exist .env_template (
        echo [信息] 正在根据模板创建 .env 配置文件...
        copy .env_template .env
        echo [重要] 请确保 .env 里的 IP 地址是 Master 电脑的真实 IP！
    ) else (
        echo [错误] 找不到配置文件模板 (.env_template)。
        pause
        exit /b
    )
)

:: 2. 激活环境
echo [1/2] 正在进入 AI 运行环境...

SET "ACT_PATH="
IF EXIST "%USERPROFILE%\miniconda3\Scripts\activate.bat" SET "ACT_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
IF EXIST "C:\ProgramData\miniconda3\Scripts\activate.bat" SET "ACT_PATH=C:\ProgramData\miniconda3\Scripts\activate.bat"

if "%ACT_PATH%"=="" (
    CALL conda.bat activate py311
) else (
    CALL "%ACT_PATH%" py311
)

:: 检查环境完整性
where celery >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未在环境中找到 Celery。环境可能损坏，请先运行 [INSTALL.bat]。
    pause
    exit /b
)

:: 3. 启动 PM2
echo [2/2] 正在启动后台服务 (PM2)...
where pm2 >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 请确保安装了 Node.js 并且环境变量已生效。
    pause
    exit /b
)

:: 强制先停止已有任务以免冲突
CALL pm2 delete localizer-remote-worker >nul 2>nul

:: 启动
CALL pm2 start worker_ecosystem.config.cjs

echo.
echo ==========================================
echo   服务已启动成功！
echo ==========================================
echo 你现在可以关闭此窗口。
echo 查看状态请运行: pm2 status
echo 停止服务请运行: pm2 stop all
echo 查看日志请运行: pm2 logs
echo.
pause
