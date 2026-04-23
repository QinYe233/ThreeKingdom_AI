# GitHub Release 上传脚本
# 使用前请先运行 gh auth login 登录

$repo = "QinYe233/ThreeKingdom_AI"
$zipPath = "e:\SanGuo.zip"
$version = "v1.0.0"
$title = "v1.0.0 - 千秋弈·群雄逐鹿"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Releases 上传工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 gh 是否已安装
try {
    $ghVersion = gh --version | Select-Object -First 1
    Write-Host "[OK] GitHub CLI 已安装：$ghVersion" -ForegroundColor Green
} catch {
    Write-Host "[X] GitHub CLI 未安装" -ForegroundColor Red
    Write-Host "请先运行：winget install GitHub.cli" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查是否已登录
try {
    $authStatus = gh auth status 2>&1
    if ($authStatus -match "Logged in") {
        Write-Host "[OK] GitHub 已登录" -ForegroundColor Green
    } else {
        Write-Host "[!] GitHub 未登录" -ForegroundColor Yellow
        Write-Host "正在启动登录流程..." -ForegroundColor Yellow
        gh auth login --hostname github.com --git-protocol https --scopes repo,workflow
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[X] 登录失败" -ForegroundColor Red
            pause
            exit 1
        }
        Write-Host "[OK] 登录成功" -ForegroundColor Green
    }
} catch {
    Write-Host "[!] 需要登录 GitHub" -ForegroundColor Yellow
    Write-Host "正在启动登录流程..." -ForegroundColor Yellow
    gh auth login --hostname github.com --git-protocol https --scopes repo,workflow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] 登录失败" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "[OK] 登录成功" -ForegroundColor Green
}

# 检查 ZIP 文件是否存在
if (-not (Test-Path $zipPath)) {
    Write-Host "[X] ZIP 文件不存在：$zipPath" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[OK] ZIP 文件已找到：$zipPath" -ForegroundColor Green
Write-Host ""
Write-Host "正在创建 Release..." -ForegroundColor Cyan

# 创建 Release
gh release create $version $zipPath `
    --repo $repo `
    --title $title `
    --notes @"
## 🎮 功能特性

- ✨ AI 驱动的三国策略游戏
- 🤖 自动化 AI 决策（支持魏蜀吴）
- 📜 史官系统记录游戏历史
- 🗺️ 可视化地图和领地系统
- 💰 经济、外交、战斗系统

## 🚀 快速开始

1. 解压 ZIP 文件
2. 运行 \`start.bat\`（Windows）或 \`start.sh\`（Mac/Linux）
3. 浏览器打开 http://localhost:5173

## ⚙️ 配置 AI

在 \`backend/data/ai_config.json\` 中配置你的 API Key

## 🛠️ 技术栈

- 后端：Python 3.11 + FastAPI
- 前端：React 18 + TypeScript + Vite
- 支持 Docker 和本地部署

## 📄 许可证

MIT License
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ 发布成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "查看发布：https://github.com/$repo/releases/tag/$version" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[X] 发布失败" -ForegroundColor Red
}

pause
