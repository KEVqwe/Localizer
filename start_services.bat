@echo off
TITLE Localizer Background Services
cd /d %~dp0
echo [1/3] Activating Conda Environment...
CALL conda activate py311
echo [2/3] Starting Background Services via PM2...
pm2 start ecosystem.config.cjs
echo [3/3] Done! Services are running in the background.
echo.
echo Use "pm2 status" to check health.
echo Use "pm2 stop all" to shut down.
timeout /t 3
exit
