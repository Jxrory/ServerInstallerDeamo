# Keycloak IAM

基于 Docker Compose 部署的 Keycloak 身份认证服务, 提供 SSO / OIDC / SAML / Admin Console, 数据存储在共享 Postgres 中。

## 目录结构

```
server-keycloak/
├── compose.yml        # 服务编排
├── .env               # 容器环境变量(模板见 .env.example)
├── README.md
└── nginx/             # 宿主机 Nginx 反代配置
    ├── keycloak       # https://keycloak.makemoney2g.com -> 127.0.0.1:5392
    ├── config_nginx.sh
    └── websocket.conf # 共享 WebSocket map(幂等安装)
```

## 启动命令

在 `DockerServices/` 目录下执行(需先启动 Postgres):

```sh
docker compose -f compose/base.yml -f compose/middleware.yml up -d postgres
docker compose --env-file ./env/db.env -f server-keycloak/compose.yml -f compose/base.yml -f compose/middleware.yml up -d keycloak
```

> `--env-file ./env/db.env` 为 compose 提供 `DB_HOST` / `DB_PORT` / `DB_USERNAME` / `DB_PASSWORD` 等插值变量, 缺失会启动失败。

## 端口说明

| 容器端口 | 宿主机端口 | 用途 |
| --- | --- | --- |
| 8080 | 5392 | HTTP 访问(生产由 Nginx 反代并终结 TLS) |

## 数据持久化

Keycloak 自身无业务数据, 全部落库到共享 Postgres 的 `keycloak` 数据库(容器网络内 `postgres:5432`)。迁移机器时确保 `keycloak` 库随 Postgres 数据卷一起迁移即可。

## 环境变量

在 `.env` 中配置(模板见 `.env.example`):

| 变量 | 说明 |
| --- | --- |
| `KC_BOOTSTRAP_ADMIN_USERNAME` | 首次启动创建的管理员用户名 |
| `KC_BOOTSTRAP_ADMIN_PASSWORD` | 管理员密码 |
| `KC_PROXY_HEADERS` | 反代头处理, 生产设为 `xforwarded` |
| `KC_HOSTNAME` | 对外访问域名, 需与 Nginx 反代一致 |
| `KC_HOSTNAME_STRICT` | 生产开启严格 hostname 校验(`true`) |
| `KC_HTTP_ENABLED` | 反代场景保持 `true`(Keycloak 自身走 HTTP, TLS 由 Nginx 终结) |

## 首次访问

启动后浏览器访问 `https://keycloak.makemoney2g.com`, 使用 `.env` 中的 `KC_BOOTSTRAP_ADMIN_USERNAME` / `KC_BOOTSTRAP_ADMIN_PASSWORD` 登录 Admin Console(`/admin`)。

## Nginx 反代(HTTPS)

线上直接使用 HTTPS: Keycloak 反代走宿主机 Nginx, 配置见 `nginx/keycloak`(`keycloak.<域名>` → `127.0.0.1:5392`), 部署:

```sh
sudo bash server-keycloak/nginx/config_nginx.sh
```

脚本会交互式询问基础域名(默认 `makemoney2g.com`, 直接回车使用默认值), 并把 `nginx/keycloak` 模板中的 `makemoney2g.com` 替换为该域名后部署到 `/etc/nginx/sites-available/keycloak`, 证书路径 `/etc/ssl/certs/<域名>/fullchain.pem` 亦同步替换。

> 证书路径约定: `/etc/ssl/certs/<域名>/fullchain.pem` + `/etc/ssl/private/<域名>/privkey.pem`, 请确保证书已按该路径放置。

反代场景下 Keycloak 自身保持 HTTP, 由 Nginx 终结 TLS, 并在 `.env` 中设置:

```sh
KC_PROXY_HEADERS=xforwarded
KC_HOSTNAME=keycloak.makemoney2g.com
KC_HOSTNAME_STRICT=true
KC_HTTP_ENABLED=true
```

修改 `.env` 后重启生效:

```sh
docker compose --env-file ./env/db.env -f server-keycloak/compose.yml -f compose/base.yml -f compose/middleware.yml restart keycloak
```

## 常见问题

- **登录页跳转 http:// 而不是 https://**: 确认 `.env` 中 `KC_PROXY_HEADERS=xforwarded` 且 Nginx 正确传递 `X-Forwarded-Proto`(模板已含)
- **`KC_HOSTNAME_STRICT` 打开后访问 400/404**: `.env` 中 `KC_HOSTNAME` 必须与浏览器访问的域名完全一致
- **连不上数据库**: 确认 Postgres 已启动且 `.env`(compose 层)从 `env/db.env` 读取到正确凭据, `keycloak` 数据库需存在(可由 Keycloak 首次启动自动创建, 前提是该库不存在)
- **改了 `.env` 不生效**: compose 的 `environment` 段是启动时注入的, 需 `restart`/`up -d` 重建容器
