@echo off
chcp 65001 >nul 2>&1
title 千秋弈·群雄逐鹿 - Stop Services / 停止服务
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "Stop-SanGuo.ps1"
if errorlevel 1 (
    echo.
    echo [错误 / ERROR] 停止服务失败，请查看上方错误信息 / Failed to stop services, please check error messages above
    echo.
    pause
)
echo.
echo 操作已完成 / Operation completed
pause
