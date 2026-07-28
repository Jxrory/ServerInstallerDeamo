### 数据库初始化

```sh
# 需要先初始化数据库
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml run --rm rails bundle exec rails db:chatwoot_prepare

# 查看数据库列表
docker exec -it postgres psql -U postgres -c "\l"
```

### 启动命令

```sh
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml up -d rails sidekiq
```