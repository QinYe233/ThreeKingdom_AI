#!/bin/bash

echo "========================================"
echo "  千秋弈·群雄逐鹿 - 一键启动"
echo "========================================"
echo ""

# 检查是否安装Docker
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "[√] 检测到Docker已安装"
    echo ""
    echo "正在使用Docker启动..."
    echo ""
    docker-compose up -d
    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================"
        echo "  启动成功！"
        echo "========================================"
        echo ""
        echo "  前端地址: http://localhost:5173"
        echo "  后端地址: http://localhost:8000"
        echo ""
        
        # 尝试打开浏览器
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:5173
        elif command -v open &> /dev/null; then
            open http://localhost:5173
        fi
    else
        echo ""
        echo "[!] Docker启动失败，请检查Docker是否正在运行"
    fi
    exit 0
fi

echo "[!] 未检测到Docker，检查本地环境..."
echo ""

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Darwin*)    PACKAGE_MANAGER="brew" ;;
    Linux*)     PACKAGE_MANAGER="apt" ;;
    *)          PACKAGE_MANAGER="unknown" ;;
esac

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[×] 未检测到Python"
    echo ""
    
    # 尝试自动安装
    if [ "$PACKAGE_MANAGER" = "brew" ]; then
        read -p "检测到Homebrew，是否自动安装Python？(y/n): " INSTALL_PYTHON
        if [ "$INSTALL_PYTHON" = "y" ] || [ "$INSTALL_PYTHON" = "Y" ]; then
            echo "正在安装Python..."
            brew install python@3.11
            echo "Python安装完成！请重新运行启动脚本。"
            exit 0
        fi
    elif [ "$PACKAGE_MANAGER" = "apt" ]; then
        read -p "检测到apt，是否自动安装Python？(y/n): " INSTALL_PYTHON
        if [ "$INSTALL_PYTHON" = "y" ] || [ "$INSTALL_PYTHON" = "Y" ]; then
            echo "正在安装Python..."
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3-pip
            echo "Python安装完成！请重新运行启动脚本。"
            exit 0
        fi
    fi
    
    echo ""
    echo "请手动安装以下软件后重试："
    echo ""
    echo "  Python 3.11+: https://www.python.org/downloads/"
    echo "  Node.js 18+:  https://nodejs.org/"
    echo ""
    echo "或者安装Docker Desktop: https://www.docker.com/products/docker-desktop"
    echo ""
    exit 1
fi
echo "[√] Python已安装"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo "[×] 未检测到Node.js"
    echo ""
    
    # 尝试自动安装
    if [ "$PACKAGE_MANAGER" = "brew" ]; then
        read -p "检测到Homebrew，是否自动安装Node.js？(y/n): " INSTALL_NODE
        if [ "$INSTALL_NODE" = "y" ] || [ "$INSTALL_NODE" = "Y" ]; then
            echo "正在安装Node.js..."
            brew install node
            echo "Node.js安装完成！请重新运行启动脚本。"
            exit 0
        fi
    elif [ "$PACKAGE_MANAGER" = "apt" ]; then
        read -p "检测到apt，是否自动安装Node.js？(y/n): " INSTALL_NODE
        if [ "$INSTALL_NODE" = "y" ] || [ "$INSTALL_NODE" = "Y" ]; then
            echo "正在安装Node.js..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt install -y nodejs
            echo "Node.js安装完成！请重新运行启动脚本。"
            exit 0
        fi
    fi
    
    echo ""
    echo "请手动安装Node.js: https://nodejs.org/"
    echo ""
    exit 1
fi
echo "[√] Node.js已安装"
echo ""

# 检查并创建虚拟环境
echo "[*] 正在检查后端环境..."
cd backend
if [ ! -d "venv" ]; then
    echo "[*] 创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[×] 创建虚拟环境失败"
        cd ..
        exit 1
    fi
fi

# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "[×] 安装后端依赖失败"
    cd ..
    exit 1
fi
echo "[√] 后端环境准备完成"
cd ..

# 安装前端依赖
echo "[*] 正在检查前端环境..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "[*] 安装前端依赖..."
    npm install --silent
    if [ $? -ne 0 ]; then
        echo "[×] 安装前端依赖失败"
        cd ..
        exit 1
    fi
fi
echo "[√] 前端环境准备完成"
cd ..
echo ""

# 启动服务
echo "[*] 正在启动服务..."
echo ""

# 根据系统选择终端启动方式
start_terminal() {
    local title="$1"
    local cmd="$2"
    
    if command -v osascript &> /dev/null; then
        # macOS
        osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)' && $cmd\""
    elif command -v gnome-terminal &> /dev/null; then
        # Linux with GNOME
        gnome-terminal --title="$title" -- bash -c "$cmd; exec bash"
    elif command -v xterm &> /dev/null; then
        # Linux with X11
        xterm -T "$title" -e bash -c "$cmd; exec bash" &
    else
        # Fallback: run in background
        eval "$cmd &"
    fi
}

# 启动后端
start_terminal "后端服务 - 千秋弈" "cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

# 等待后端启动
echo "[*] 等待后端启动..."
sleep 3

# 启动前端
start_terminal "前端服务 - 千秋弈" "cd frontend && npm run dev"

# 等待前端启动
echo "[*] 等待前端启动..."
sleep 5

echo ""
echo "========================================"
echo "  启动成功！"
echo "========================================"
echo ""
echo "  前端地址: http://localhost:5173"
echo "  后端地址: http://localhost:8000"
echo ""
echo "  提示：关闭终端窗口可停止对应服务"
echo ""

# 尝试打开浏览器
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
elif command -v open &> /dev/null; then
    open http://localhost:5173
fi
