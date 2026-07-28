### 初始化数据库

```sh
# 在共享 postgres 中创建 litellm 数据库
docker exec -it postgres psql -U postgres -c "CREATE DATABASE litellm;"
```

### 启动命令

```sh
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-litellm/compose.yml -f compose/base.yml -f compose/middleware.yml up -d litellm
```

启动后访问地址：http://localhost:4000/ui/
