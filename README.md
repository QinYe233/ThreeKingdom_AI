# 千秋弈·群雄逐鹿

> AI 驱动的三国策略沙盒游戏 · 谋定天下，一统中原

![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![React](https://img.shields.io/badge/React-19-blue.svg)
![Tauri](https://img.shields.io/badge/Tauri-2-orange.svg)

---

## 游戏特色

- **AI 驱动**：魏蜀吴等多方势力均由独立 AI 控制，支持流式输出与深度思考
- **自动对战**：配置 AI 后一键托管，观看群雄逐鹿
- **史官系统**：AI 生成编年叙事，完整记录战局演变
- **策略丰富**：进攻、骚扰、征兵、发展、调兵、迁都、征税等多种指令
- **战争迷雾**：各势力仅能看到己方领土及相邻区域
- **特殊中立势力**：山越、南中、凉州、公孙度、士燮等特殊中立势力，攻占其领地可获得额外奖励
- **存档系统**：支持手动存档与自动存档，最多 20 个存档位
- **桌面端支持**：Tauri 打包为 Windows 桌面应用，一键安装

---

## 快速开始

### Windows 桌面版（推荐）

无需安装 Python、Node.js 等开发环境，下载即可游玩：

1. 前往 [Releases](https://github.com/QinYe233/ThreeKingdom_AI/releases) 下载最新版安装包（`SanGuo_x.x.x_x64-setup.exe`）
2. 双击运行安装程序，按提示完成安装
3. 启动游戏，配置 AI 模型后即可开始

### Windows 开发模式

1. **下载项目**
   - `git clone https://github.com/QinYe233/ThreeKingdom_AI.git`

2. **启动游戏**
   - 双击运行 `启动游戏.bat`
   - 首次运行会自动检测并提示安装缺失的依赖（Python、Node.js）

3. **访问游戏**
   - 浏览器自动打开，或手动访问 http://localhost:5173

4. **停止服务**
   - 双击运行 `停止服务.bat`

### Mac / Linux

```bash
# 1. 克隆仓库
git clone https://github.com/QinYe233/ThreeKingdom_AI.git
cd ThreeKingdom_AI

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 安装前端依赖
cd ../frontend
npm install

# 4. 启动后端（新终端）
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 启动前端（新终端）
cd frontend
npm run dev

# 6. 访问游戏
# 打开浏览器访问 http://localhost:5173
```

### Docker 部署

```bash
docker-compose up -d
```

> 国内用户可使用镜像加速：
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> npm install --registry=https://registry.npmmirror.com
> ```

---

## AI 配置

### 支持的 AI 模型

| 模型 | 说明 | 推荐指数 |
|------|------|---------|
| **GPT-4** | OpenAI 最强模型 | ⭐⭐⭐⭐⭐ |
| **GPT-3.5-turbo** | 性价比高 输出规范 | ⭐⭐⭐⭐ |
| **DeepSeek** | 性价比高 思考较快 | ⭐⭐⭐⭐⭐ |
| **自定义 API** | 支持兼容 OpenAI 格式的 API | ⭐⭐⭐⭐⭐ |

### 配置步骤

1. 点击界面右上角 **「设置」** 按钮
2. 选择 AI 模型类型
3. 输入 API Key（从对应平台获取）
4. 如使用自定义 API，填写 Base URL
5. 点击 **「保存」**

> API Key 是敏感信息，请勿泄露给他人！

---

## 游戏操作

### 地图操作

| 操作 | 说明 |
|------|------|
| **左键点击区块** | 选中区块，查看详细信息 |
| **中键按住拖拽** | 平移地图 |
| **中键滚轮** | 缩放地图（0.8x - 3.0x） |
| **星形标记** | 表示该区块是国家首都 |

### 界面功能

| 按钮 | 功能 |
|------|------|
| **自动** | 启动/停止自动播放，AI 自动决策 |
| **设置** | 配置 AI 模型（API Key、模型选择等） |
| **史官** | 查看历史记录和叙事日志 |
| **返回** | 返回主菜单（自动存档） |
| **存档** | 保存/加载游戏进度 |

### 区块信息

选中区块后，右侧面板显示：
- **区块名称**：如"许昌"、"成都"等
- **归属势力**：魏/蜀/吴/中立等
- **兵力**：当前驻军数量
- **人力**：可征兵人口
- **发展度**：经济水平

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **桌面端** | Tauri 2 (Rust) + NSIS 安装包 |
| **前端** | React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + Zustand + GSAP |
| **地图** | Canvas 2D + GeoJSON |
| **后端** | FastAPI + Python 3.11+ + Uvicorn |
| **AI** | OpenAI API / DeepSeek / 自定义兼容 API |
| **通信** | REST API + Server-Sent Events (SSE) |
| **部署** | Docker Compose / Windows Bat 脚本 / Tauri 桌面打包 |

---

## 项目结构

```
ThreeKingdom_AI/
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── ai/             # AI 客户端与决策逻辑
│   │   ├── api/            # API 路由（game, map, ai, save）
│   │   ├── core/           # 核心引擎（战斗、外交、经济、迷雾、编年史）
│   │   ├── data/maps/      # 三国地图 GeoJSON 数据
│   │   ├── models/         # 数据模型
│   │   └── main.py         # 入口
│   └── requirements.txt
├── frontend/               # React + Vite 前端
│   ├── src/
│   │   ├── components/     # UI 组件（地图、面板、播放器等）
│   │   ├── hooks/          # React Hooks（自动播放、地图动画）
│   │   ├── stores/         # Zustand 状态管理
│   │   ├── utils/          # 工具函数（API、音频、SSE）
│   │   └── types/          # TypeScript 类型定义
│   └── package.json
├── src-tauri/              # Tauri 桌面端
│   ├── src/main.rs         # Rust 入口（后端进程管理、窗口控制）
│   └── tauri.conf.json     # Tauri 配置
├── Music/                  # 背景音乐资源
├── docs/                   # 文档与地图数据
├── 启动游戏.bat             # Windows 启动游戏（自动检测依赖）
├── 停止服务.bat             # Windows 停止服务
└── docker-compose.yml      # Docker 部署配置
```

---

## 常见问题

### Q1: 启动时提示"Python 不是内部或外部命令"

重新安装 Python，勾选 "Add Python to PATH" 选项。

### Q2: 启动时提示"npm 不是内部或外部命令"

重新安装 Node.js。

### Q3: AI 决策时报错 "API Key invalid"

检查 API Key 是否正确，确认账户余额是否充足。

### Q4: 地图显示空白或区块无法点击

检查 `docs/three_kingdoms.geojson` 文件是否存在，刷新浏览器页面。

### Q5: 如何重置游戏？

停止游戏，删除 `backend/data/game_state.json` 文件，重新启动。

### Q6: Tauri 构建失败

确保已安装 Rust 工具链（`rustup`），且前端已执行 `npm install` 和 `npm run build`。

### Q7: 存档文件保存在哪里？

存档文件保存在 `backend/data/saves/` 目录下（Windows 下相对于项目根目录，位于 backend 目录中）。

### Q8: API Key 安全吗？

API Key 存储在本地 `backend/data/ai_config.json` 文件中，仅保存在您的本机，绝不会发送到任何第三方服务器。

---

## 许可证

本项目采用 [CC BY-NC-SA 4.0](LICENSE) 协议开源。

- 允许：个人学习、研究、非商业用途、修改和分享
- 禁止：商业用途（未经作者书面许可）
- 要求：衍生作品必须使用相同协议，并注明原作者

---

天下大势，分久必合，合久必分
