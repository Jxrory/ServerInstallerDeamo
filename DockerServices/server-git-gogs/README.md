# Gogs Git Server

基于 Docker Compose 部署的轻量级 Git 服务(Gogs), 提供 Web 管理界面 + SSH 访问。

## 目录结构

```
server-git-gogs/
├── compose.yml        # 服务编排
├── .env               # 容器环境变量(模板见 .env.example)
├── README.md
└── nginx/             # 宿主机 Nginx 反代配置
    ├── gogs           # https://git.makemoney2g.com -> 127.0.0.1:4647
    ├── config_nginx.sh
    └── websocket.conf # 共享 WebSocket map(幂等安装)
```

## 启动命令

在 `DockerServices/` 目录下执行:

```sh
docker compose -f server-git-gogs/compose.yml -f compose/base.yml up -d git-gogs
```

## 端口说明

| 容器端口 | 宿主机端口 | 用途 |
| --- | --- | --- |
| 3000 | 4647 | Web HTTP 访问 |
| 22 | 10022 | SSH 访问(避免与宿主机 22 冲突) |

## 数据持久化

Gogs 数据目录 `/data` 通过 bind mount 挂载到宿主机 `/opt/Data/Hub/Gogs`:

| 子目录 | 内容 |
| --- | --- |
| `gogs/conf/app.ini` | Gogs 配置文件 |
| `git/` | 仓库数据 |
| `ssh/` | SSH 授权 key |
| `log/` | 日志 |

迁移机器时直接拷贝 `/opt/Data/Hub/Gogs` 即可, 无需进容器导出。

## 环境变量

在 `.env` 中配置(模板见 `.env.example`):

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `RUN_CROND` | `false` | 启用内置定时任务(如每日备份) |
| `TZ` | `Asia/Shanghai` | 容器时区 |

## 首次安装(Web 安装向导)

首次启动后浏览器访问 `http://<服务器IP>:4647`, 按向导填写:

- **数据库**: 单机选 SQLite3 即可, 数据自动落在 `/opt/Data/Hub/Gogs` 下; 如需 MySQL/Postgres 按向导填连接信息
- **域名**: `git.makemoney2g.com`(需与 Nginx 反代一致)
- **SSH 端口**: `22`(容器内端口; 外部连接用宿主机 `10022`)
- **应用 URL**: `https://git.makemoney2g.com/`
- **管理员账号**: 向导会创建第一个管理员账号

> 安装完成后也可手动改 `/opt/Data/Hub/Gogs/gogs/conf/app.ini` 再重启容器。

## Nginx 反代(HTTPS)

Gogs 反代走宿主机 Nginx, 配置见 `nginx/gogs`(`git.<域名>` → `127.0.0.1:4647`), 部署:

```sh
sudo bash server-git-gogs/nginx/config_nginx.sh
```

脚本会交互式询问基础域名(默认 `makemoney2g.com`, 直接回车使用默认值), 并把 `nginx/gogs` 模板中的 `makemoney2g.com` 替换为该域名后部署到 `/etc/nginx/sites-available/gogs`, 证书路径 `/etc/ssl/certs/<域名>/fullchain.pem` 亦同步替换。

> 证书路径约定: `/etc/ssl/certs/<域名>/fullchain.pem` + `/etc/ssl/private/<域名>/privkey.pem`, 请确保证书已按该路径放置。

反代场景下 Gogs 自身保持 `PROTOCOL = http`, 由 Nginx 终结 TLS, 在 `app.ini` 中设置:

```ini
[server]
PROTOCOL = http
DOMAIN = git.makemoney2g.com
ROOT_URL = https://git.makemoney2g.com/
SSH_PORT = 22    ; 容器内 SSH 端口
```

`app.ini` 位置: 宿主机 `/opt/Data/Hub/Gogs/gogs/conf/app.ini`(容器内 `/data/gogs/conf/app.ini`), 修改后重启生效:

```sh
docker compose -f server-git-gogs/compose.yml -f compose/base.yml restart git-gogs
```

## SSH 访问

外部 SSH 使用宿主机 `10022` 端口:

```sh
# 验证连通
ssh -p 10022 -T git@<服务器IP>

# 克隆
git clone ssh://git@<服务器IP>:10022/<owner>/<repo>.git

# 已有仓库关联远程
git remote add origin ssh://git@<服务器IP>:10022/<owner>/<repo>.git
git push -u origin master
```

## 常见问题

- **修改端口/挂载路径**: 编辑 `compose.yml` 后执行 `docker compose -f server-git-gogs/compose.yml -f compose/base.yml up -d` 重建
- **改了 app.ini 不生效**: 确认改的是 bind mount 下的文件(`/opt/Data/Hub/Gogs/gogs/conf/app.ini`)并重启容器
- **HTTP push 大仓库 413**: 已在上游 Nginx 配置 `client_max_body_size 100m`, 若仍超限可自行调大
