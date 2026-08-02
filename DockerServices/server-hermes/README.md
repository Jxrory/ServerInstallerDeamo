## 启动命令

```sh
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose -f server-hermes/compose.yml -f compose/base.yml up -d hermes-gateway
```

## UID/GID 配置(重要)

容器镜像内部的 `hermes` 用户默认 UID/GID 为 `10000:10000`, 而宿主机普通用户(如 `ubuntu`)通常是 `1000:1000`。二者不一致会导致 bind-mount 的 `profile/` 目录(cron、memories、sessions、skills)出现权限问题: 容器写入的文件宿主机读不了, 宿主机写入的文件容器读不了。

**部署时务必**在 `.env` 里把 `HERMES_UID` / `HERMES_GID` 设为运行 docker 命令的宿主机用户的 UID/GID。镜像的 s6-overlay 启动脚本会据此把内部 `hermes` 用户 remap 到这个值, 从而消除权限错配。

```sh
# 查看当前用户的 UID/GID
id -u && id -g

# 写入 .env (例如 ubuntu 用户)
HERMES_UID=1000
HERMES_GID=1000
```

如果容器曾以错误的 UID(如 10000)运行过, 已有文件的属主需要手动修复:

```sh
sudo chown -R $(id -u):$(id -g) server-hermes/profile
```

## LLM 配置

Hermes 通过 Bifrost 网关(`http://bifrost:8080/v1`,走 ops-network 容器网络)访问大语言模型。

- **配置文件**:`deploy/config.yaml` —— bind-mount 到容器 `/opt/data/config.yaml`,版本可控、可迁移。`custom_providers.bifrost` 定义了网关地址、API key 环境变量名(`key_env: BIFROST_API_KEY`)和默认模型。
- **API key**:`deploy/.env` 里的 `BIFROST_API_KEY=...` —— 通过 compose `env_file` 注入容器环境,运行时按 `key_env` 名读取。
- **默认模型**:`opencode-go/deepseek-v4-flash`。切换模型改 `model.default` 和 `custom_providers.bifrost.default_model` 即可(Bifrost 上可用模型见 `GET http://bifrost:8080/v1/models`)。

> config.yaml 里的 `provider: bifrost` 是 `custom_providers` 里的命名条目;Hermes 运行时把它解析为 `provider=custom`,从对应条目取 `base_url` 和 `key_env`。

## 迁移到新机器

1. 拷贝整个 `server-hermes/` 目录(含 `deploy/config.yaml` 和 `deploy/.env`)。
2. 确保 `deploy/.env` 里 `BIFROST_API_KEY` 等密钥已填(从 `.env.example` 复制后补全)。
3. 执行启动命令即可。config.yaml 是 bind-mount,不需要从数据卷恢复。
