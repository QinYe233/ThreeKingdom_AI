@echo off
chcp 65001 >nul 2>&1
title 千秋弈·群雄逐鹿 - Start Game / 启动游戏
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "SanGuo.ps1"
if errorlevel 1 (
    echo.
    echo [错误 / ERROR] 启动失败，请查看上方错误信息 / Startup failed, please check error messages above
    echo.
    pause
)
echo.
echo 程序已退出 / Program exited
pause
