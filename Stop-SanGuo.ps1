$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "SanGuo - Stop Services"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SanGuo - Stop Services" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Stopping services..." -ForegroundColor Yellow

$stopped = $false
$errors = @()

try {
    $backendProc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $backendProc) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
    if ($backendProc) {
        Write-Host "  Stopped backend (port 8000)" -ForegroundColor Green
    }
} catch {
    $errors += "Failed to stop backend on port 8000: $_"
}

try {
    $frontendProc = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $frontendProc) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
    if ($frontendProc) {
        Write-Host "  Stopped frontend (port 5173)" -ForegroundColor Green
    }
} catch {
    $errors += "Failed to stop frontend on port 5173: $_"
}

try {
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*SanGuo*" -or $_.CommandLine -like "*uvicorn*"
    } | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
} catch {
    $errors += "Failed to stop Python processes: $_"
}

try {
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*SanGuo*" -or $_.CommandLine -like "*vite*"
    } | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
} catch {
    $errors += "Failed to stop Node processes: $_"
}

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "[WARNING] Errors occurred:" -ForegroundColor Yellow
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

Write-Host ""
if ($stopped) {
    Write-Host "[OK] Services stopped" -ForegroundColor Green
} else {
    Write-Host "[!] No running services found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
