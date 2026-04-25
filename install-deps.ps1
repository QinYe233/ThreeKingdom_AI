$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "SanGuo - 安装依赖"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  千秋弈·群雄逐鹿 - 依赖安装工具" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Command {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-Python {
    try {
        $version = python --version 2>&1
        return $version -match "Python 3\.(1[1-9]|[2-9][0-9])"
    } catch {
        return $false
    }
}

function Test-NodeJS {
    try {
        $version = node --version 2>&1
        return $version -match "v(1[8-9]|[2-9][0-9])"
    } catch {
        return $false
    }
}

Write-Host "[*] 检查系统环境..." -ForegroundColor Yellow
Write-Host ""

$needPython = -not (Test-Python)
$needNode = -not (Test-NodeJS)

if (-not $needPython -and -not $needNode) {
    Write-Host "[OK] 所有依赖已安装！" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Python: $(python --version 2>&1)" -ForegroundColor Cyan
    Write-Host "  Node.js: $(node --version 2>&1)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host "需要安装以下依赖：" -ForegroundColor Yellow
if ($needPython) { Write-Host "  - Python 3.11+" -ForegroundColor White }
if ($needNode) { Write-Host "  - Node.js 18+" -ForegroundColor White }
Write-Host ""

if (-not (Test-Command winget)) {
    Write-Host "[!] 未检测到 winget，请手动安装依赖：" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Python: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "  Node.js: https://nodejs.org/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "[OK] 检测到 winget，将自动安装依赖" -ForegroundColor Green
Write-Host ""

if ($needPython) {
    Write-Host "[*] 正在安装 Python 3.11..." -ForegroundColor Yellow
    Write-Host "    这可能需要几分钟，请耐心等待..." -ForegroundColor Gray
    $result = winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements --silent 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Python 3.11 安装成功" -ForegroundColor Green
    } else {
        Write-Host "[!] Python 安装可能失败，请检查输出" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($needNode) {
    Write-Host "[*] 正在安装 Node.js LTS..." -ForegroundColor Yellow
    Write-Host "    这可能需要几分钟，请耐心等待..." -ForegroundColor Gray
    $result = winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements --silent 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Node.js 安装成功" -ForegroundColor Green
    } else {
        Write-Host "[!] Node.js 安装可能失败，请检查输出" -ForegroundColor Yellow
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "  依赖安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "重要提示：" -ForegroundColor Yellow
Write-Host "  1. 请关闭当前窗口" -ForegroundColor White
Write-Host "  2. 重新打开一个新的命令行窗口" -ForegroundColor White
Write-Host "  3. 再次运行游戏启动器" -ForegroundColor White
Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
