#!/bin/bash
set -e

echo "更新软件包..."
sudo apt update

echo "安装依赖..."
sudo apt install -y ca-certificates curl gnupg

echo "添加 Docker GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "添加 Docker 软件源..."
echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
| sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "安装 Docker Engine 和 Compose..."
sudo apt update

sudo apt install -y \
docker-ce \
docker-ce-cli \
containerd.io \
docker-buildx-plugin \
docker-compose-plugin

echo "启动 Docker..."
sudo systemctl enable docker
sudo systemctl start docker

echo "添加当前用户到 docker 组..."
sudo usermod -aG docker $USER

echo "检查版本:"
docker --version
docker compose version

echo "安装完成，请重新登录终端后使用 docker 无 sudo 权限"