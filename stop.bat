@echo off
chcp 65001 >nul 2>&1
mode con cp select=65001 >nul 2>&1

title SanGuo - Stop Services

echo ========================================
echo   SanGuo - Stop Services
echo ========================================
echo.

REM 检查Docker是否在运行
docker ps >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Docker is running, stopping Docker services...
    docker compose down
    if %errorlevel% equ 0 (
        echo [OK] Docker services stopped
    ) else (
        echo [!] Failed to stop Docker services
    )
    echo.
    pause
    exit /b 0
)

REM 停止本地服务
echo [*] Stopping local services...
echo.

REM 停止后端 (uvicorn 运行在 python 进程中)
taskkill /f /fi "WINDOWTITLE eq Backend - SanGuo*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *uvicorn*" >nul 2>&1

REM 停止前端
taskkill /f /fi "WINDOWTITLE eq Frontend - SanGuo*" >nul 2>&1
taskkill /f /im node.exe /fi "WINDOWTITLE eq *npm*" >nul 2>&1

echo [OK] Services stopped
echo.
pause
