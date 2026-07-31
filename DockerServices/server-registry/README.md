## 启动命令

```sh
docker compose -f registry-server/compose.yml -f compose/base.yml up -d registry
```

## 客户端配置

```json
{
  "registry-mirrors": [
    "http://127.0.0.1:5000"
  ]
}
```

## regctl 查看容器内镜像内容
```bash
# 下载最新版本的 regctl
curl -L https://github.com/regclient/regclient/releases/latest/download/regctl-linux-amd64 > regctl
chmod 755 regctl
sudo mv regctl /usr/local/bin/
```

### 常用命令

配置 regctl 对该 Registry 禁用 TLS
```bash
regctl registry set localhost:5000 --tls disabled
```

- 列出所有镜像：

```bash
regctl repo ls localhost:5000
```

- 查看镜像的标签：

```bash
regctl tag ls localhost:5000/library/nginx
```

- 查看镜像的详细信息（如大小、创建时间、包含的层等）：

```bash
regctl manifest get localhost:5000/library/nginx:latest
```

### 推送本地镜像到仓库

- 推送镜像：先为本地镜像打上包含仓库地址的标签，然后推送。

```bash
docker tag nginx:latest 192.168.1.100:5000/my-nginx:latest
docker push 192.168.1.100:5000/my-nginx:latest

```

- 拉取镜像：直接从私有仓库拉取即可

```bash
docker pull 192.168.1.100:5000/my-nginx:latest
```
