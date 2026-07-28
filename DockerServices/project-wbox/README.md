### 初始化数据库

```sh
docker exec -it postgres psql -U postgres -c "CREATE DATABASE wonderbox;"
```

### 启动命令

```sh
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-wbox/compose.yml -f compose/base.yml -f compose/middleware.yml up -d app admin
```