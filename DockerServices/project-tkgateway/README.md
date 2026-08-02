### 初始化数据库

```sh
docker exec -it postgres psql -U postgres -c "CREATE DATABASE tkgateway;"
```

### 启动命令

```sh
docker compose --env-file project-tkgateway/.env --env-file ./env/db.env --env-file ./env/redis.env -f project-tkgateway/compose.yml -f compose/base.yml -f compose/middleware.yml up -d tk-gateway
```