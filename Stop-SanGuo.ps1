$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "SanGuo - Stop Services"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SanGuo - Stop Services" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Info "Stopping services..."

$stopped = $false
$errors = @()

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

try {
    $windows = Get-Process | Where-Object { $_.MainWindowTitle -like "*SanGuo*" }
    foreach ($win in $windows) {
        Stop-Process -Id $win.Id -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }
} catch {
    $errors += "Failed to stop SanGuo windows: $_"
}

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Warning "Errors occurred:"
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

Write-Host ""
if ($stopped) {
    Write-Success "Services stopped"
} else {
    Write-Info "No running services found"
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
