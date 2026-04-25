#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
依赖检查和下载工具
自动检测并安装 Python 3.11+ 和 Node.js 18+
"""
import subprocess
import sys
import os


def run_command(cmd, shell=False):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_python():
    """检查 Python 版本"""
    success, output = run_command(["python", "--version"])
    if not success:
        return False, None

    version_str = output.strip()
    try:
        # 解析版本号 (Python 3.11.0 -> 3.11)
        version_part = version_str.split()[1]
        major, minor = map(int, version_part.split(".")[:2])
        version = (major, minor)
        return True, version
    except (IndexError, ValueError):
        return True, None


def check_nodejs():
    """检查 Node.js 版本"""
    success, output = run_command(["node", "--version"])
    if not success:
        return False, None

    version_str = output.strip().lstrip('v')
    try:
        # 解析版本号 (v20.0.0 -> 20.0)
        version_part = version_str.split(".")[0]
        major = int(version_part)
        version = (major,)
        return True, version
    except (IndexError, ValueError):
        return True, None


def check_winget():
    """检查 winget 是否可用"""
    success, _ = run_command(["winget", "--version"])
    return success


def install_python():
    """使用 winget 安装 Python"""
    if not check_winget():
        print("[ERROR] winget 不可用，无法自动安装 Python")
        print("[INFO] 请手动下载并安装 Python 3.11+: https://www.python.org/downloads/")
        return False

    print("[INFO] 正在使用 winget 安装 Python 3.11...")
    success, output = run_command([
        "winget", "install", "Python.Python.3.11",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent"
    ])

    if success:
        print("[SUCCESS] Python 3.11 安装成功")
        print("[WARNING] 请关闭当前程序，重新打开命令行后再继续")
        return True
    else:
        print("[ERROR] Python 安装失败:")
        print(output)
        return False


def install_nodejs():
    """使用 winget 安装 Node.js"""
    if not check_winget():
        print("[ERROR] winget 不可用，无法自动安装 Node.js")
        print("[INFO] 请手动下载并安装 Node.js 18+: https://nodejs.org/")
        return False

    print("[INFO] 正在使用 winget 安装 Node.js LTS...")
    success, output = run_command([
        "winget", "install", "OpenJS.NodeJS.LTS",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent"
    ])

    if success:
        print("[SUCCESS] Node.js LTS 安装成功")
        print("[WARNING] 请关闭当前程序，重新打开命令行后再继续")
        return True
    else:
        print("[ERROR] Node.js 安装失败:")
        print(output)
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("依赖检查工具")
    print("=" * 50)
    print()

    # 检查 Python
    print("[CHECK] 检查 Python...")
    python_installed, python_version = check_python()
    if python_installed and python_version:
        major, minor = python_version
        if major == 3 and minor >= 11:
            print(f"[OK] Python 已安装: {major}.{minor}.x")
        else:
            print(f"[WARNING] Python 版本过低: {major}.{minor}.x (需要 3.11+)")
            python_installed = False
    else:
        print("[MISSING] Python 未安装")

    # 检查 Node.js
    print("[CHECK] 检查 Node.js...")
    node_installed, node_version = check_nodejs()
    if node_installed and node_version:
        major = node_version[0]
        if major >= 18:
            print(f"[OK] Node.js 已安装: {major}.x.x")
        else:
            print(f"[WARNING] Node.js 版本过低: {major}.x.x (需要 18+)")
            node_installed = False
    else:
        print("[MISSING] Node.js 未安装")

    print()
    print("=" * 50)

    # 检查是否需要安装
    needs_install = not python_installed or not node_installed

    if not needs_install:
        print("[SUCCESS] 所有依赖已安装，可以继续！")
        return 0

    print("[WARNING] 需要安装缺失的依赖:")
    if not python_installed:
        print("  - Python 3.11+")
    if not node_installed:
        print("  - Node.js 18+")
    print()

    # 尝试自动安装
    if check_winget():
        print("[INFO] 检测到 winget，可以自动安装依赖")
        print()

        if not python_installed:
            install_python()
            print()
        if not node_installed:
            install_nodejs()
            print()

        print("=" * 50)
        print("[INFO] 安装完成后，请:")
        print("  1. 关闭当前程序")
        print("  2. 打开新的命令行窗口")
        print("  3. 重新运行游戏启动器")
        print("=" * 50)
        return 0
    else:
        print("[ERROR] 未检测到 winget，无法自动安装")
        print()
        print("[INFO] 请手动安装以下软件:")
        print("  - Python 3.11+: https://www.python.org/downloads/")
        print("  - Node.js 18+:  https://nodejs.org/")
        print()
        print("[INFO] 或者安装 Windows Package Manager (winget):")
        print("  https://github.com/microsoft/winget-cli")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
