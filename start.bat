@echo off
chcp 65001 >nul 2>&1
mode con cp select=65001 >nul 2>&1

title SanGuo Launcher

echo ========================================
echo   SanGuo - Quick Start
echo ========================================
echo.

REM 检查是否安装Docker
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Docker detected
    echo.
    echo Starting with Docker...
    echo.
    
    REM 使用 docker compose（新版命令）
    docker compose up -d
    if %errorlevel% equ 0 (
        echo.
        echo ========================================
        echo   Started successfully!
        echo ========================================
        echo.
        echo   Frontend: http://localhost:5173
        echo   Backend:  http://localhost:8000
        echo.
        echo   Press any key to open the game...
        pause >nul
        start http://localhost:5173
    ) else (
        echo.
        echo [!] Docker start failed.
        echo     Please check if Docker Desktop is running.
        echo.
        pause
    )
    exit /b 0
)

echo [!] Docker not detected, checking local environment...
echo.

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python not found
    
    REM 检查winget
    winget --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo winget detected. Can auto-install Python.
        echo.
        set /p INSTALL_PYTHON="Auto-install Python? (Y/N): "
        if /i "%INSTALL_PYTHON%"=="Y" (
            echo.
            echo Installing Python, please wait...
            winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            echo.
            echo Python installed! Please close this window and run the script again.
            pause
            exit /b 0
        )
    )
    
    echo.
    echo Please install the following software and try again:
    echo.
    echo   Python 3.11+: https://www.python.org/downloads/
    echo   Node.js 18+:  https://nodejs.org/
    echo.
    echo Or install Docker Desktop: https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 0
)
echo [OK] Python found

REM 检查Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js not found
    
    REM 检查winget
    winget --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo winget detected. Can auto-install Node.js.
        echo.
        set /p INSTALL_NODE="Auto-install Node.js? (Y/N): "
        if /i "%INSTALL_NODE%"=="Y" (
            echo.
            echo Installing Node.js, please wait...
            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
            echo.
            echo Node.js installed! Please close this window and run the script again.
            pause
            exit /b 0
        )
    )
    
    echo.
    echo Please install Node.js: https://nodejs.org/
    echo.
    pause
    exit /b 0
)
echo [OK] Node.js found
echo.

REM 检查并创建虚拟环境
echo [*] Checking backend environment...
cd /d "%~dp0backend"
if not exist "venv" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [X] Failed to create virtual environment
        cd ..
        pause
        exit /b 0
    )
)

REM 激活虚拟环境并安装依赖
call venv\Scripts\activate
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [X] Failed to install backend dependencies
    cd ..
    pause
    exit /b 0
)
echo [OK] Backend environment ready
cd ..

REM 安装前端依赖
echo [*] Checking frontend environment...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [*] Installing frontend dependencies...
    call npm install --silent
    if %errorlevel% neq 0 (
        echo [X] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 0
    )
)
echo [OK] Frontend environment ready
cd ..
echo.

REM 启动服务
echo [*] Starting services...
echo.

REM 启动后端
start "Backend - SanGuo" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM 等待后端启动
echo [*] Waiting for backend...
timeout /t 3 /nobreak >nul

REM 启动前端
start "Frontend - SanGuo" cmd /k "cd /d "%~dp0frontend" && npm run dev"

REM 等待前端启动
echo [*] Waiting for frontend...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Started successfully!
echo ========================================
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo   Tip: Close the popup windows to stop services
echo.
echo   Press any key to open the game...
pause >nul
start http://localhost:5173
