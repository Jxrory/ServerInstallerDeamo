## 启动命令

```sh
docker compose -f server-hermes/compose.yml -f compose/base.yml up -d hermes-gateway
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
