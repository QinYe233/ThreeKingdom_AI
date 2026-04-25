param(
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "SanGuo - Three Kingdoms Strategy Game"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = $PWD.Path }

function Write-Header {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  SanGuo - Three Kingdoms Strategy Game" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Stop-Services {
    Write-Header
    Write-Host "[*] Stopping services..." -ForegroundColor Yellow
    
    $stopped = $false
    
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*SanGuo*" -or $_.CommandLine -like "*uvicorn*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*SanGuo*" -or $_.CommandLine -like "*vite*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    $windows = Get-Process | Where-Object { $_.MainWindowTitle -like "*SanGuo*" }
    foreach ($win in $windows) {
        Stop-Process -Id $win.Id -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
    
    if ($stopped) {
        Write-Host "[OK] Services stopped" -ForegroundColor Green
    } else {
        Write-Host "[!] No running services found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

function Test-Command {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Install-Python {
    Write-Warning "Python not detected"
    Write-Host ""

    if (Test-Command winget) {
        Write-Host "Auto-install Python 3.11? (Y/N): " -NoNewline -ForegroundColor Cyan
        $choice = Read-Host
        if ($choice -eq 'Y' -or $choice -eq 'y') {
            Write-Info "Installing Python, please wait..."
            $result = winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements --silent 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Success "Python installed, please restart this program"
                Write-Host ""
                pause
                exit 0
            } else {
                Write-Host ""
                Write-Error "Python installation failed:"
                Write-Host $result
                Write-Host ""
                Write-Info "Please install Python 3.11+ manually: https://www.python.org/downloads/"
                Write-Host ""
                pause
                exit 1
            }
        }
    }

    Write-Host ""
    Write-Info "Please install Python 3.11+: https://www.python.org/downloads/"
    Write-Host ""
    pause
    exit 1
}

function Install-NodeJS {
    Write-Warning "Node.js not detected"
    Write-Host ""

    if (Test-Command winget) {
        Write-Host "Auto-install Node.js LTS? (Y/N): " -NoNewline -ForegroundColor Cyan
        $choice = Read-Host
        if ($choice -eq 'Y' -or $choice -eq 'y') {
            Write-Info "Installing Node.js, please wait..."
            $result = winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements --silent 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Success "Node.js installed, please restart this program"
                Write-Host ""
                pause
                exit 0
            } else {
                Write-Host ""
                Write-Error "Node.js installation failed:"
                Write-Host $result
                Write-Host ""
                Write-Info "Please install Node.js 18+ manually: https://nodejs.org/"
                Write-Host ""
                pause
                exit 1
            }
        }
    }

    Write-Host ""
    Write-Info "Please install Node.js 18+: https://nodejs.org/"
    Write-Host ""
    pause
    exit 1
}

function Start-Backend {
    param($BackendDir)

    Write-Info "Starting backend service..."

    $venvPath = Join-Path $BackendDir "venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $venvPath)) {
        Write-Info "Creating Python virtual environment..."
        try {
            Push-Location $BackendDir
            python -m venv venv
            Pop-Location
        } catch {
            Write-Error "Failed to create virtual environment: $_"
            Write-Host ""
            pause
            exit 1
        }
    }

    if (-not (Test-Path $venvPython)) {
        $venvPython = "python"
    }

    $requirementsPath = Join-Path $BackendDir "requirements.txt"
    Write-Info "Installing backend dependencies..."
    try {
        & $venvPython -m pip install -r $requirementsPath
    } catch {
        Write-Warning "Backend dependency installation had issues, continuing..."
    }

    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $venvPython
        $startInfo.Arguments = "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"
        $startInfo.WorkingDirectory = $BackendDir
        $startInfo.UseShellExecute = $true
        $startInfo.WindowStyle = "Normal"

        $null = [System.Diagnostics.Process]::Start($startInfo)
        Write-Success "Backend started (port 8000)"
    } catch {
        Write-Error "Failed to start backend: $_"
        Write-Host ""
        pause
        exit 1
    }
}

function Start-Frontend {
    param($FrontendDir)

    Write-Info "Starting frontend service..."

    $nodeModulesPath = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModulesPath)) {
        Write-Info "Installing frontend dependencies..."
        try {
            Push-Location $FrontendDir
            npm install --silent 2>$null
            Pop-Location
        } catch {
            Write-Error "Failed to install frontend dependencies: $_"
            Write-Host ""
            pause
            exit 1
        }
    }

    try {
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "npm"
        $startInfo.Arguments = "run", "dev"
        $startInfo.WorkingDirectory = $FrontendDir
        $startInfo.UseShellExecute = $true
        $startInfo.WindowStyle = "Normal"

        $null = [System.Diagnostics.Process]::Start($startInfo)
        Write-Success "Frontend started (port 5173)"
    } catch {
        Write-Error "Failed to start frontend: $_"
        Write-Host ""
        pause
        exit 1
    }
}

function Open-Browser {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
}

if ($Stop) {
    Stop-Services
}

Write-Header

Write-Info "Checking environment..."
Write-Host ""

try {
    if (-not (Test-Command python)) {
        Install-Python
    }
    Write-Success "Python installed"

    if (-not (Test-Command node)) {
        Install-NodeJS
    }
    Write-Success "Node.js installed"
} catch {
    Write-Error "Environment check failed: $_"
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Info "Starting services..."
Write-Host ""

$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"

try {
    Start-Backend -BackendDir $BackendDir
    Start-Sleep -Seconds 2
    Start-Frontend -FrontendDir $FrontendDir
} catch {
    Write-Error "Failed to start services: $_"
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Started successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Tip: Close popup windows to stop services" -ForegroundColor Gray
Write-Host ""

Write-Host "Open browser? (Y/N): " -NoNewline -ForegroundColor Cyan
$openBrowser = Read-Host
if ($openBrowser -eq 'Y' -or $openBrowser -eq 'y' -or $openBrowser -eq '') {
    Open-Browser
}

Write-Host ""
Write-Host "Press any key to exit launcher (services will keep running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
