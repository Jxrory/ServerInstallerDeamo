### 数据库初始化

```sh
# 需要先初始化数据库
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml run --rm rails bundle exec rails db:chatwoot_prepare

# 查看数据库列表
docker exec -it postgres psql -U postgres -c "\l"

# 删除某个数据库
# docker exec -it postgres psql -U postgres -c "DROP DATABASE chatwoot_production;"
```

### 启动命令

```sh
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml up -d rails sidekiq

docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml restart rails sidekiq
```

### 开启所有的企业功能

```sh
# docker compose run --rm rails bundle exec rails enterprise:features:enable_all
docker compose --env-file ./env/postgres.env --env-file ./env/redis.env -f project-chatwoot/compose.yml -f compose/base.yml -f compose/middleware.yml run --rm -e RAILS_ENV=production rails bundle exec rails enterprise:features:enable_all
```