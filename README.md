# 千秋弈·群雄逐鹿

> AI 驱动的三国策略游戏 · 谋定天下，一统中原

![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)

---

## 🎮 游戏特色

- **AI 驱动**：魏蜀吴三方势力均由独立 AI 控制，展现不同战略风格
- **自动对战**：配置 AI 后一键托管，观看群雄逐鹿
- **史官系统**：完整记录每回合决策与战局演变
- **策略丰富**：进攻、征兵、发展、外交、战斗等多种指令

---

## 🚀 快速开始

### Windows 用户

1. **下载项目**
   - 克隆仓库：`git clone https://github.com/QinYe233/ThreeKingdom_AI.git`
   - 或下载 [ZIP 压缩包](https://github.com/QinYe233/ThreeKingdom_AI/archive/refs/heads/main.zip)

2. **安装依赖**
   - 双击运行 `安装依赖.bat`

3. **启动游戏**
   - 双击运行 `启动游戏.bat`

4. **访问游戏**
   - 打开浏览器访问：http://localhost:5173

### Mac/Linux 用户

```bash
# 1. 克隆仓库
git clone https://github.com/QinYe233/ThreeKingdom_AI.git
cd ThreeKingdom_AI

# 2. 安装依赖
cd backend
pip install -r requirements.txt
cd ../frontend
npm install

# 3. 启动后端（新终端）
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. 启动前端（新终端）
cd frontend
npm run dev

# 5. 访问游戏
# 打开浏览器访问：http://localhost:5173
```

> 💡 **提示**：如果下载速度较慢，可以使用国内镜像：
> ```bash
> # Python 镜像
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
>
> # Node.js 镜像
> npm install --registry=https://registry.npmmirror.com
> ```

---

## ⚙️ AI 配置

### 支持的 AI 模型

| 模型 | 说明 | 推荐指数 |
|------|------|---------|
| **GPT-4** | OpenAI 最强模型 | ⭐⭐⭐⭐⭐ |
| **GPT-3.5-turbo** | 性价比高 | ⭐⭐⭐⭐ |
| **DeepSeek** | 国产大模型，性价比高 | ⭐⭐⭐⭐⭐ |
| **自定义 API** | 支持兼容 OpenAI 格式的 API | ⭐⭐⭐ |

### 配置步骤

1. 点击界面右上角的 **「设置」** 按钮
2. 选择 AI 模型类型
3. 输入 API Key（从对应平台获取）
4. 如使用自定义 API，填写 Base URL
5. 点击 **「保存」**

### 获取 API Key

**OpenAI (GPT-4)**：
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册/登录账号
3. 进入 API Keys 页面
4. 点击 "Create new secret key"

**DeepSeek**：
1. 访问 [DeepSeek 官网](https://www.deepseek.com/)
2. 注册/登录账号
3. 进入 API Keys 页面
4. 创建新的 API Key

> ⚠️ **注意**：API Key 是敏感信息，请勿泄露给他人！

---

## 🎯 游戏操作

### 地图操作

| 操作 | 说明 |
|------|------|
| **左键点击区块** | 选中区块，查看详细信息 |
| **中键按住拖拽** | 平移地图 |
| **中键滚轮** | 缩放地图（范围：0.8x - 3.0x） |
| **⭐ 星形标记** | 表示该区块是国家首都 |

### 界面功能

| 按钮 | 功能 |
|------|------|
| **自动** | 启动/停止自动播放，AI 自动决策 |
| **设置** | 配置 AI 模型（API Key、模型选择等） |
| **史官** | 查看历史记录和叙事日志 |
| **外交** | 查看各国之间的外交关系 |

### 区块信息

选中区块后，右侧面板会显示：
- **区块名称**：如"许昌"、"成都"等
- **归属势力**：魏/蜀/吴/中立
- **兵力**：当前驻军数量
- **人力**：可征兵人口
- **发展度**：经济水平

---

## 🛠️ 技术栈

| 前端 | 后端 | AI |
|------|------|------|
| React 18 + TypeScript | FastAPI + Python 3.11 | 多 LLM 支持 |
| Canvas 2D 地图 | 异步流式响应 | GPT-4 / DeepSeek / 自定义 |

---

## 📦 部署方式

### Docker（推荐）

```bash
docker-compose up -d
```

### 本地运行

**环境要求**：
- Python 3.11+
- Node.js 18+

---

## ❓ 常见问题

### Q1: 启动时提示"Python 不是内部或外部命令"

**解决方法**：重新安装 Python，勾选 "Add Python to PATH" 选项。

### Q2: 启动时提示"npm 不是内部或外部命令"

**解决方法**：重新安装 Node.js。

### Q3: AI 决策时报错 "API Key invalid"

**解决方法**：检查 API Key 是否正确，确认是否有余额。

### Q4: 地图显示空白或区块无法点击

**解决方法**：检查 `docs/three_kingdoms.geojson` 文件是否存在，刷新浏览器页面。

### Q5: 如何重置游戏？

**解决方法**：停止游戏，删除 `backend/data/game_state.json` 文件，重新启动游戏。

---

## 📄 许可证

本项目采用 [CC BY-NC-SA 4.0](LICENSE) 协议开源。

- ✅ **允许**：个人学习、研究、非商业用途、修改和分享
- ❌ **禁止**：商业用途（未经作者书面许可）
- 🔄 **要求**：衍生作品必须使用相同协议，并注明原作者

详见 [LICENSE](LICENSE) 文件。

---

## 🏆 天下大势，分久必合，合久必分

##————此文档由AI生成，已经人工审核————##
