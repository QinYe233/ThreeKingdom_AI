# 千秋弈·群雄逐鹿 - 部署指南

## 快速启动

### Windows用户
双击运行 `start.bat`

### Mac/Linux用户
```bash
chmod +x start.sh
./start.sh
```

**脚本会自动检测并提示安装缺失的依赖！**

---

## 部署方式

### 方式一：Docker部署（推荐）

**前置条件：**
- 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)

**启动步骤：**
1. 确保Docker Desktop正在运行
2. 双击 `start.bat`（Windows）或运行 `./start.sh`（Mac/Linux）
3. 浏览器自动打开 http://localhost:5173

**停止服务：**
- Windows: 双击 `stop.bat`
- Mac/Linux: 运行 `docker-compose down`

---

### 方式二：本地环境部署

**前置条件：**
- Python 3.11+ ([下载](https://www.python.org/downloads/))
- Node.js 18+ ([下载](https://nodejs.org/))

**启动步骤：**
1. 双击 `start.bat`（Windows）或运行 `./start.sh`（Mac/Linux）
2. 脚本会自动：
   - 检测缺失的依赖
   - **提示自动安装**（Windows使用winget，Mac使用Homebrew，Linux使用apt）
   - 创建Python虚拟环境
   - 安装所有依赖
   - 启动服务
3. 浏览器自动打开 http://localhost:5173

**手动启动：**

后端：
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：
```bash
cd frontend
npm install
npm run dev
```

---

## 自动安装依赖

启动脚本支持自动安装缺失的依赖：

| 系统 | 包管理器 | 支持安装 |
|------|----------|----------|
| Windows | winget | Python, Node.js |
| macOS | Homebrew | Python, Node.js |
| Linux | apt | Python, Node.js |

如果系统没有对应的包管理器，脚本会提供下载链接供手动安装。

---

## AI配置

游戏启动后，在设置界面配置AI模型的API：

1. 点击"设置"按钮
2. 为每个国家（魏、蜀、吴）配置：
   - 模型名称（如：gpt-4o、deepseek-chat）
   - API Key
   - Base URL（如：https://api.openai.com/v1）
3. 点击"测试连接"验证配置
4. 保存配置

---

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 5173 | Vite开发服务器 |
| 后端 | 8000 | FastAPI服务 |

---

## 常见问题

### Q: 启动失败，提示端口被占用
A: 检查5173或8000端口是否被其他程序占用，关闭占用程序后重试

### Q: 提示缺少Python/Node.js
A: 脚本会提示自动安装，选择Y即可；或手动下载安装

### Q: Docker启动失败
A: 确保Docker Desktop正在运行，并已启用WSL2（Windows）

### Q: AI配置失败
A: 检查API Key是否正确，Base URL是否包含 `/v1` 后缀

### Q: 地图无法显示
A: 确保后端服务正常启动，检查浏览器控制台是否有错误

### Q: Windows提示"无法运行脚本"
A: 以管理员身份运行PowerShell，执行：
```powershell
Set-ExecutionPolicy RemoteSigned
```

---

## 项目结构

```
SanGuo/
├── backend/           # 后端代码
│   ├── app/
│   │   ├── api/       # API接口
│   │   ├── ai/        # AI决策引擎
│   │   ├── core/      # 核心逻辑
│   │   └── models/    # 数据模型
│   ├── data/          # 游戏数据
│   └── requirements.txt
├── frontend/          # 前端代码
│   ├── src/
│   │   ├── components/
│   │   ├── stores/
│   │   └── App.tsx
│   └── package.json
├── docker-compose.yml
├── start.bat          # Windows启动脚本（支持自动安装）
├── start.sh           # Mac/Linux启动脚本（支持自动安装）
└── stop.bat           # Windows停止脚本
```

---

## 分享给他人

1. 将整个 `SanGuo` 文件夹打包成zip
2. 发送给对方
3. 对方解压后双击 `start.bat` 即可
4. 脚本会自动检测环境并提示安装缺失的依赖
