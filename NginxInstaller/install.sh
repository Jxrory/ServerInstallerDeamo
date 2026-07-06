#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_DIR="$BASE_DIR/conf"

NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo "=============================="
echo " Nginx Safe Installer"
echo "=============================="

# 1. 检查 nginx 是否存在
echo "==> 检查 nginx"
if ! command -v nginx >/dev/null 2>&1; then
  echo "==> 安装 nginx"
  sudo apt update
  sudo apt install nginx -y
else
  echo "nginx 已安装"
fi

# 2. 检查 conf 目录
if [ ! -d "$CONF_DIR" ]; then
  echo "❌ conf 目录不存在: $CONF_DIR"
  exit 1
fi

# 3. 🔥 关键：预检查 nginx 配置
echo "==> 预检查 nginx 配置（不会安装，只验证）"

shopt -s nullglob

ERRORS=0

for file in "$CONF_DIR"/*; do
  [ -f "$file" ] || continue

  name="$(basename "$file")"

  echo "-> 检查: $name"

  # 使用 nginx -t -c 临时测试（关键点）
  if ! sudo nginx -t -c "$file" >/dev/null 2>&1; then
    echo "❌ 配置错误: $name"
    echo "--------------------------------"
    sudo nginx -t -c "$file"
    echo "--------------------------------"
    ERRORS=1
  else
    echo "✔ 通过"
  fi
done

# 如果有错误，直接退出
if [ "$ERRORS" -ne 0 ]; then
  echo ""
  echo "=============================="
  echo "❌ 检测到错误配置，已终止部署"
  echo "👉 请先修复 conf/ 中的 nginx 配置"
  echo "=============================="
  exit 1
fi

echo ""
echo "=============================="
echo "✔ 所有配置校验通过，开始部署"
echo "=============================="

# 4. 配置 ufw
echo "==> 配置 ufw（80/443）"
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 80 >/dev/null 2>&1 || true
  sudo ufw allow 443 >/dev/null 2>&1 || true
fi

# 5. 部署配置
echo "==> 部署 nginx 配置"

for file in "$CONF_DIR"/*; do
  [ -f "$file" ] || continue

  name="$(basename "$file")"

  TARGET_CONF="$NGINX_AVAILABLE/$name"
  LINK="$NGINX_ENABLED/$name"

  echo "-> 部署 $name"

  sudo cp "$file" "$TARGET_CONF"

  if [ ! -L "$LINK" ]; then
    sudo ln -s "$TARGET_CONF" "$LINK"
  fi
done

# 6. 最终 nginx 全局校验（双保险）
echo "==> 最终 nginx 配置检查"
if ! sudo nginx -t; then
  echo "❌ nginx 全局配置错误，回滚失败部署"
  exit 1
fi

# 7. reload
echo "==> 重载 nginx"
sudo systemctl reload nginx

echo "=============================="
echo "✅ 部署完成"
echo "=============================="