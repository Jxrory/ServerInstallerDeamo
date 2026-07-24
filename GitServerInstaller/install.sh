#!/bin/bash

set -e

# ==============================
# Git Server 一键初始化脚本（Ubuntu / Debian）
# ==============================

# 检查配置
if [ -z "$GIT_USER" ] || [ -z "$GIT_HOME" ] || [ -z "$GIT_REPO_BASE" ]; then
    echo "❌ 缺少环境变量"
    exit 1
fi

REPO_BASE="${GIT_HOME}/${GIT_REPO_BASE}"

# 获取 git-shell 路径（不同系统可能不同）
SHELL_PATH=$(which git-shell || echo "/usr/bin/git-shell")

echo "=============================="
echo " 开始安装 Git Server"
echo "=============================="

# # 1. 更新软件源并安装 git 和 openssh-server
# sudo apt update -y
# sudo apt install -y git openssh-server

# 3. 创建 git 用户（如果不存在）
if id "$GIT_USER" &>/dev/null; then
    echo "[OK] git 用户已存在"
else
    # 创建 git 用户，并指定 home 和 shell
    sudo useradd -m -d $GIT_HOME -s $SHELL_PATH $GIT_USER
    sudo passwd -l $GIT_USER
fi

# 4. 强制使用 git-shell（禁止普通 shell 登录）
sudo usermod -s $SHELL_PATH $GIT_USER

# 5. 配置 SSH 公钥目录
sudo mkdir -p $GIT_HOME/.ssh
sudo touch $GIT_HOME/.ssh/authorized_keys

# 设置权限（非常重要，否则 SSH 会拒绝）
sudo chmod 700 $GIT_HOME/.ssh
sudo chmod 600 $GIT_HOME/.ssh/authorized_keys
sudo chown -R $GIT_USER:$GIT_USER $GIT_HOME/.ssh

# 6. 创建仓库目录
sudo mkdir -p $REPO_BASE
sudo chown -R $GIT_USER:$GIT_USER $REPO_BASE

# 7. 创建示例裸仓库
if [ ! -d "$REPO_BASE/test.git" ]; then
    sudo -u $GIT_USER git init --bare $REPO_BASE/test.git
    echo "[OK] 已创建示例仓库 test.git"
fi

# 8. 修复 git 家目录权限
sudo chown -R $GIT_USER:$GIT_USER $GIT_HOME

echo "=============================="
echo " Git Server 安装完成"
echo "=============================="
echo "仓库路径: $REPO_BASE"
echo ""
echo "客户端克隆示例："
echo "git clone git@服务器IP:$REPO_BASE/test.git"
echo "=============================="