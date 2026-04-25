@echo off
chcp 65001 >nul 2>&1
title 千秋弈·群雄逐鹿 - 安装依赖
cd /d "%~dp0"

echo ========================================
echo   依赖安装工具
echo ========================================
echo.

REM 首先尝试使用 Python 脚本
if exist "check_dependencies.py" (
    echo [INFO] 使用 Python 依赖检查工具...
    echo.
    python check_dependencies.py
    if errorlevel 1 (
        echo.
        echo [错误] Python 依赖检查失败
        echo.
    )
) else (
    echo [INFO] 使用 PowerShell 依赖安装脚本...
    echo.
    powershell -ExecutionPolicy Bypass -File "install-deps.ps1"
    if errorlevel 1 (
        echo.
        echo [错误] PowerShell 安装失败
        echo.
    )
)

echo.
echo ========================================
echo   按任意键退出...
echo ========================================
pause
