
### 启动基础服务

```bash
docker compose --env-file ./env/db.env --env-file ./env/redis.env -f compose/base.yml -f compose/middleware.yml -f compose/observability.yml -f compose/tools.yml up -d
```
