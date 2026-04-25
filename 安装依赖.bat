@echo off
chcp 65001 >nul 2>&1
title 千秋弈·群雄逐鹿 - Install Dependencies / 安装依赖
cd /d "%~dp0"

echo ========================================
echo   Dependency Installation Tool / 依赖安装工具
echo ========================================
echo.

REM 首先尝试使用 Python 脚本
if exist "check_dependencies.py" (
    echo [INFO] Using Python dependency checker / 使用 Python 依赖检查工具...
    echo.
    python check_dependencies.py
    if errorlevel 1 (
        echo.
        echo [错误 / ERROR] Python dependency check failed / Python 依赖检查失败
        echo.
    )
) else (
    echo [INFO] Using PowerShell installation script / 使用 PowerShell 依赖安装脚本...
    echo.
    powershell -ExecutionPolicy Bypass -File "install-deps.ps1"
    if errorlevel 1 (
        echo.
        echo [错误 / ERROR] PowerShell installation failed / PowerShell 安装失败
        echo.
    )
)

echo.
echo ========================================
echo   Press any key to exit... / 按任意键退出...
echo ========================================
pause
