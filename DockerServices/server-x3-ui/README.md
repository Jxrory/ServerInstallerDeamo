# 3x-ui (Xray 面板)

基于 Docker Compose 部署的 3x-ui 面板(Xray Core 多协议管理: VLESS / VMess / Trojan / Reality 等)。面板端口只绑定宿主机回环地址, 公网访问统一由宿主机 Nginx 终结 TLS 反代, Xray 节点端口按需直接对外暴露。

## 架构

```
Internet
   |
  443 (Nginx TLS)
   |
   ├── x3ui.<域名>/          -> 127.0.0.1:2053 (面板)
   └── 节点端口(如 8443)     -> Docker 端口映射 (Xray 入站)
```

## 目录结构

```
server-x3-ui/
├── compose.yml        # 服务编排
├── .env               # 端口/开关配置(模板见 .env.example)
├── db/                # 面板数据库持久化(/etc/x-ui)
├── cert/              # 放置给 Xray 用的证书(/root/cert)
├── README.md
└── nginx/             # 宿主机 Nginx 反代配置
    ├── x3-ui          # https://x3ui.makemoney2g.com -> 127.0.0.1:2053
    ├── config_nginx.sh
    └── websocket.conf # 共享 WebSocket map(幂等安装)
```

## 启动命令

```sh
docker compose --env-file server-x3-ui/.env -f server-x3-ui/compose.yml up -d 3x-ui
```

首次启动后查看随机生成的面板入口(用户名/密码/路径):

```sh
docker logs 3x-ui
```

## 端口说明

| 宿主机端口 | 用途 | 对外 |
| --- | --- | --- |
| 2053 | 3x-ui 面板(仅绑定 `127.0.0.1`) | 否, 经 Nginx 反代 |
| 8443 | Xray 节点入站(如 VLESS Reality) | 是 |

> 面板创建入站时监听端口需与 `.env` 中 `XRAY_NODE_PORT` 一致才能对外访问; 若新增其它节点端口, 在 `compose.yml` 的 `ports` 追加映射后 `up -d` 重建。

## 数据持久化

- `db/` → 容器 `/etc/x-ui`: 面板配置、入站、客户端数据。迁移机器时整体拷贝即可。
- `cert/` → 容器 `/root/cert`: 给 Xray 入站(TLS 类协议)使用的证书/私钥。

## 环境变量

在 `.env` 中配置(模板见 `.env.example`):

| 变量 | 说明 |
| --- | --- |
| `XUI_PANEL_PORT` | 面板监听端口, 默认 `2053`(Nginx 反代目标) |
| `XRAY_NODE_PORT` | 节点入站端口, 默认 `8443`, 与面板中入站保持一致 |
| `XRAY_VMESS_AEAD_FORCED` | VMess AEAD 强制开关, 默认 `false` |
| `XUI_ENABLE_FAIL2BAN` | 容器内 fail2ban 防爆破, 默认 `true` |

## Nginx 反代(HTTPS)

证书已按仓库约定路径放置(`/etc/ssl/certs/<域名>/fullchain.pem` + `/etc/ssl/private/<域名>/privkey.pem`)后执行:

```sh
sudo bash server-x3-ui/nginx/config_nginx.sh
```

脚本会交互式询问基础域名(默认 `makemoney2g.com`, 直接回车使用默认值), 把 `nginx/x3-ui` 模板中的域名替换后部署到 `/etc/nginx/sites-available/x3-ui`, 并做证书存在性检查、`nginx -t` 校验后 reload。

### 防火墙

只放行 80 / 443 / 节点端口:

```sh
ufw allow 80,443/tcp
ufw allow 8443/tcp
```

不要放行 2053(面板仅限本机 + Nginx 访问)。

## 安全建议

- 首次登录后立即修改默认账号 `admin/admin`
- 面板设置中将 URI 路径改为随机串(如 `/a8f92kd/`), 避免 `/panel/` 被扫描
- 定期升级镜像: `docker compose pull && docker compose up -d`

## 常见问题

- **改了 `.env` 不生效**: compose 的端口/env 是启动时注入的, 需 `up -d` 重建容器而非 `restart`
- **节点不通**: 检查入站监听端口是否与宿主机映射端口一致、防火墙是否放行
- **WS 节点想共用 443**: 见 `nginx/x3-ui` 中注释的 `/ws` location 示例
