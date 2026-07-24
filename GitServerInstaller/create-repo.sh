#!/bin/bash

set -e

# 检查配置
if [ -z "$GIT_USER" ] || [ -z "$GIT_HOME" ] || [ -z "$GIT_REPO_BASE" ]; then
    echo "❌ 缺少环境变量"
    exit 1
fi


REPO_BASE="${GIT_HOME}/${GIT_REPO_BASE}"


REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "❌ 请提供仓库名称"
    exit 1
fi


if [[ "$REPO_NAME" != *.git ]]; then
    REPO_NAME="${REPO_NAME}.git"
fi


REPO_PATH="${REPO_BASE}/${REPO_NAME}"


echo "创建仓库:"
echo "$REPO_PATH"


if [ -d "$REPO_PATH" ]; then
    echo "❌ 已存在"
    exit 1
fi


sudo -u "$GIT_USER" git init --bare "$REPO_PATH"

sudo chown -R "$GIT_USER:$GIT_USER" "$REPO_PATH"


echo "✅ 完成"