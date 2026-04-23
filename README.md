# 千秋弈·群雄逐鹿

一款基于 AI 的三国策略游戏，支持魏、蜀、吴三方势力，每个国家都由独立的 AI 驱动。

## 快速开始

### Windows 用户
双击运行 `start.bat`

### Mac/Linux 用户
```bash
chmod +x start.sh
./start.sh
```

**脚本会自动：**
- 检测 Docker（如有则使用 Docker 启动）
- 检测 Python 和 Node.js（如无则提示自动安装）
- 安装所有依赖
- 启动游戏服务

## 配置 AI

游戏启动后，在设置界面配置 AI：

1. 点击"设置"按钮
2. 为魏、蜀、吴配置 AI 模型：
   - 模型名称（如：gpt-4o、deepseek-chat）
   - API Key
   - Base URL
3. 测试连接并保存

## 游戏玩法

- **目标**：统一天下，称帝建国
- **行动**：进攻、征兵、发展、征税、调兵、外交等
- **特色**：每个国家由不同 AI 驱动，具有独特战略风格

## 技术栈

- **前端**：React + TypeScript + Three.js
- **后端**：FastAPI + Python
- **AI**：支持多种大语言模型

## 许可证

MIT License
