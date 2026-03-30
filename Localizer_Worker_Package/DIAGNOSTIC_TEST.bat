@echo off
CHCP 65001 >nul
TITLE Localizer Worker - 诊断测试工具
SETLOCAL EnableDelayedExpansion

echo ===========================================
echo   Localizer 节点连接性与环境诊断
echo ===========================================

:: 1. 获取 Master IP (从 .env 读取)
if not exist .env (
    echo [错误] 找不到 .env 文件，请先运行 START_WORKER.bat。
    pause
    exit /b
)

:: 解析 IP
for /f "tokens=2 delims==" %%a in ('findstr "CELERY_BROKER_URL" .env') do (
    set "URL=%%a"
)
:: 粗略提取 IP (去掉 redis://:pass@ 和 :6379/0)
for /f "tokens=2 delims=@" %%a in ("!URL!") do (
    for /f "tokens=1 delims=:" %%b in ("%%a") do (
        set "MASTER_IP=%%b"
    )
)

echo [诊断] Master 电脑 IP: !MASTER_IP!

:: 测试 Ping
echo [1/4] 测试物理连接 (Ping)...
ping -n 1 !MASTER_IP! >nul
if %ERRORLEVEL% EQU 0 (
    echo [成功] 能够 Ping 通 Master 电脑。
) else (
    echo [失败] 无法连通 Master 电脑。请检查两台电脑是否在同一个局域网。
)

:: 测试 Redis 端口
echo [2/4] 测试 Redis 通信 (端口 6379)...
powershell -command "Test-NetConnection !MASTER_IP! -Port 6379" | findstr "TcpTestSucceeded" >temp_res.txt
set /p RES=<temp_res.txt
del temp_res.txt
echo !RES! | findstr "True" >nul
if %ERRORLEVEL% EQU 0 (
    echo [成功] 能够访问 Master 电脑的 Redis 端口。
) else (
    echo [失败] Redis 端口 (6379) 不通！请检查 Master 电脑的防火墙是否已开放 6379 端口。
)

:: 测试 Python 环境
echo [3/4] 测试本地 Python 环境与包...
SET "ACT_PATH="
IF EXIST "%USERPROFILE%\miniconda3\Scripts\activate.bat" SET "ACT_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
IF EXIST "C:\ProgramData\miniconda3\Scripts\activate.bat" SET "ACT_PATH=C:\ProgramData\miniconda3\Scripts\activate.bat"

if "%ACT_PATH%"=="" (
    CALL conda.bat activate py311 >nul 2>nul
) else (
    CALL "%ACT_PATH%" py311 >nul 2>nul
)

python -c "import worker.src.celery_tasks; print('Module Load OK')" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [成功] 本机 Python 依赖加载正常。
) else (
    echo [失败] Python 模块加载报错。请重跑 [INSTALL.bat] 或查看 pm2 logs。
)

:: 检查 FFmpeg
echo [4/4] 检查 FFmpeg 状态...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [成功] FFmpeg 已正确安装在系统中。
) else (
    echo [失败] 未找到 FFmpeg，视频合成功能将失效。
)

echo.
echo ==========================================
echo   诊断结束！
echo ==========================================
pause
