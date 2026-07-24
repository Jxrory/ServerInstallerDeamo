#!/usr/bin/env bash
set -euo pipefail

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

# 4. 配置 ufw
echo "==> 配置 ufw（80/443）"
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 80 >/dev/null 2>&1 || true
  sudo ufw allow 443 >/dev/null 2>&1 || true
fi

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