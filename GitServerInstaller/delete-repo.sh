#!/bin/bash

set -e

# ==============================
# 检查环境变量
# ==============================

if [ -z "$GIT_USER" ] || [ -z "$GIT_HOME" ] || [ -z "$GIT_REPO_BASE" ]; then
    echo "❌ 缺少环境变量"
    exit 1
fi


REPO_BASE="${GIT_HOME}/${GIT_REPO_BASE}"


# ==============================
# 获取仓库名称
# ==============================

REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "❌ 错误：请提供仓库名称"
    echo "用法: delete-repo <repo_name>"
    exit 1
fi


# 自动补全 .git

if [[ "$REPO_NAME" != *.git ]]; then
    REPO_NAME="${REPO_NAME}.git"
fi


REPO_PATH="${REPO_BASE}/${REPO_NAME}"


echo "=============================="
echo "准备删除 Git 仓库"
echo "仓库: $REPO_NAME"
echo "路径: $REPO_PATH"
echo "=============================="


# ==============================
# 检查仓库是否存在
# ==============================

if ! sudo -u "$GIT_USER" test -d "$REPO_PATH"; then
    echo "❌ 仓库不存在: $REPO_PATH"
    exit 1
fi


# ==============================
# 删除确认
# ==============================

# read -p "⚠️ 确认删除？(yes/no): " CONFIRM

# if [ "$CONFIRM" != "yes" ]; then
#     echo "取消删除"
#     exit 0
# fi


# ==============================
# 删除仓库
# ==============================

sudo -u "$GIT_USER" rm -rf "$REPO_PATH"


echo "=============================="
echo "✅ 仓库删除成功"
echo "已删除: $REPO_PATH"
echo "=============================="