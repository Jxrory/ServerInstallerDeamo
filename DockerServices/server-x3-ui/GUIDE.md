# 3x-ui 全链路配置指南

本文档描述从零搭建到客户端可用的**完整链路**配置方法, 包括 DNS、证书、面板、节点入站、订阅服务与防火墙。

> 当前服务器(influence-os-server)已完成 1~5 步, 第 6 步(创建入站)需在面板中按场景操作。

---

## 1. 架构总览

```
                         Internet
                            |
                      Cloudflare CDN (可选代理)
                     /            \
                 443 (代理)      2096 / 8443 (仅 DNS 模式或 CF 支持端口)
                    |                 |
                 Nginx (TLS 终结)     |
                 /        \           |
          面板路径       /ws 路径      |
              |            |          |
        127.0.0.1:2053    |          |
              |            |          |
         ┌──── Docker: 3x-ui ────┐    |
         |  Panel :2053          |    |
         |  Sub   :2096  ←———————|————┘  (订阅服务自带 TLS, 直接对外)
         |  Xray inbound :8443 ←—|————  (Reality 直连, 不经 Nginx)
         └───────────────────────┘
              |
         ./db 持久化  ./cert 证书挂载(/root/cert)
```

三条流量线:

| 流量 | 入口 | 是否走 Nginx |
| --- | --- | --- |
| 管理面板 | `https://x3ui.<域名>/<随机路径>/` | ✅ TLS 由 Nginx 终结 |
| 订阅链接 | `https://x3ui.<域名>:2096/<subId>` | ❌ 容器内自带 TLS |
| 节点(Reality 等) | `<IP 或域名>:8443` | ❌ Xray 自带 TLS |

---

## 2. 前置条件

### 2.1 DNS(Cloudflare)

| 记录 | 类型 | 内容 | 代理状态 |
| --- | --- | --- | --- |
| `x3ui` | A | 服务器 IP | 已开启(橙云) |

- 面板走 CF 代理可隐藏源站 IP;
- **节点若用 Reality/VLESS-TCP 直连, 客户端地址建议填服务器 IP 或另建灰云(DNS only)记录**, 因为 Reality 握手特征不适合经 CF 中转。

### 2.2 证书

本站为**灰云直连域名**, 浏览器/订阅客户端直连源站, 必须使用公网受信证书(Cloudflare Origin CA 证书仅 CF 边缘信任, 灰云下无效):

```sh
sudo certbot certonly --nginx -d x3ui.<域名>   # Let's Encrypt, 自动续期
```

Nginx 反代引用 `/etc/letsencrypt/live/x3ui.<域名>/fullchain.pem`; 订阅服务使用的副本放在 `server-x3-ui/cert/`(挂载进容器 `/root/cert`)。

### 2.3 防火墙

```sh
ufw allow 80,443/tcp    # Nginx
ufw allow 2096/tcp      # 订阅(CF 支持代理的 HTTPS 端口)
ufw allow 8443/tcp      # 节点
# 不要放行 2053(面板仅回环)
```

> ⚠️ 启用 ufw 前先梳理本机所有在跑服务的端口, 避免 SSH(22)之外的服务被误伤。

---

## 3. 部署容器

```sh
cd ~/ServerInstallerDeamo/DockerServices
cp server-x3-ui/.env.example server-x3-ui/.env   # 按需修改端口
docker compose --env-file server-x3-ui/.env -f server-x3-ui/compose.yml up -d 3x-ui
```

修改 `.env`(如换节点端口)后必须重建而非 restart:

```sh
docker compose --env-file server-x3-ui/.env -f server-x3-ui/compose.yml up -d --force-recreate 3x-ui
```

---

## 4. 面板初始化

1. 浏览器打开 `https://x3ui.<域名>/<随机路径>/`
2. 首次登录后**立即修改密码**: 面板设置 → 账户
3. 确认 URI 路径为随机串(已配置), 避免默认 `/panel/` 被扫描

命令行查看/重置入口信息:

```sh
docker exec 3x-ui /app/x-ui setting -show
# 忘记密码时重置:
docker exec 3x-ui /app/x-ui setting -username <用户名> -password <新密码> -webBasePath /<随机串>/
docker restart 3x-ui
```

---

## 5. 订阅服务(已配置)

订阅用于把多个节点聚合成一条 URL, 客户端导入后自动拉取/更新节点。

当前配置(写入 `db/x-ui.db` 的 `settings` 表):

| 键 | 值 | 说明 |
| --- | --- | --- |
| `subEnable` | `true` | 开启订阅 |
| `subPort` | `2096` | 对外端口(CF 支持代理的 HTTPS 端口) |
| `subCertFile` | `/root/cert/fullchain.pem` | 容器内证书(宿主机 `cert/`) |
| `subKeyFile` | `/root/cert/privkey.pem` | 私钥, 配了即启用 HTTPS |
| `subDomain` | `x3ui.<域名>` | 生成的订阅链接使用该主机名 |

最终订阅地址形如: `https://x3ui.<域名>:2096/sub/<subId>`, 在面板"订阅"页复制即可。

证书续期后同步副本并重启(certbot 自动续期时也会触发):

```sh
sudo cp /etc/letsencrypt/live/<域名>/fullchain.pem /etc/letsencrypt/live/<域名>/privkey.pem \
   ~/ServerInstallerDeamo/DockerServices/server-x3-ui/cert/
docker restart 3x-ui
```

一键部署续期钩子(可选, 自动完成上述动作):

```sh
sudo tee /etc/letsencrypt/renewal-hooks/deploy/x3ui-sync.sh <<'HOOK'
#!/usr/bin/env bash
cp /etc/letsencrypt/live/x3ui.makemoney2g.com/{fullchain.pem,privkey.pem} \
   ~/ServerInstallerDeamo/DockerServices/server-x3-ui/cert/
docker restart 3x-ui
HOOK
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/x3ui-sync.sh
```

---

## 6. 创建节点入站(核心步骤)

登录面板 → 入站列表 → 添加入站, 按场景二选一或都建:

### 方案 A: VLESS + Reality(推荐, 直连不经 CF)

| 项目 | 值 |
| --- | --- |
| 监听端口 | `8443`(须等于 `.env` 的 `XRAY_NODE_PORT`) |
| 协议 | VLESS |
| 安全 | Reality |
| 目标网站(dest) | `gateway.icloud.com:443`(实测可用, **勿用微软系**) |
| SNI(serverNames) | `gateway.icloud.com`(必须与 dest 同域且客户端一致) |
| 私钥/公钥 | 面板一键生成, 公钥给客户端 |

> ⚠️ **dest 目标站选型是 Reality 能否工作的关键**: `www.microsoft.com` 等 Akamai 系站点会在 TLS 握手中途断流, 导致所有客户端"认证通过但连接被关闭"(表现为 timeout)。Xray 官方也警告微软系目标会增加服务器 IP 被墙风险。推荐 `gateway.icloud.com` / `www.samsung.com` / `dl.google.com` 等。改 dest 后 serverNames 与客户端 SNI 必须同步更换。

特点: 无需域名与证书、抗探测能力强, 但**暴露服务器真实 IP**, 且该端口不能走 CF。

### 方案 B: VLESS + WebSocket + TLS(走 CF, 可套 CDN)

1. `.env` 增加 WS 内部端口映射(如 `127.0.0.1:10000:10000`, 仅回环), 重建容器
2. 面板添加入站: 协议 VLESS, 端口 `10000`, 传输 `ws`, path 设为 `/ws`(自定义)
3. 取消 `nginx/x3-ui` 模板中 `/ws` location 的注释并把上游端口改成 `10000`, 重新执行 `config_nginx.sh`
4. 客户端地址填 `x3ui.<域名>`、端口 `443`、传输 ws、path 与 TLS 开启

特点: 真实 IP 被 CF 隐藏、可复用 443, 但延迟增加, 速度受 CF 限制。

### 端口对照表

| 端口 | 用途 | 绑定 | 备注 |
| --- | --- | --- | --- |
| 2053 | 面板 | 127.0.0.1 | 仅 Nginx 反代访问 |
| 2096 | 订阅 HTTPS | 0.0.0.0 | CF 支持代理端口之一 |
| 8443 | 节点(方案A) | 0.0.0.0 | CF 支持代理端口之一, 但 Reality 不走 CF |
| 10000 | 节点 ws(方案B) | 127.0.0.1 | 经 Nginx 443 对外 |

---

## 7. 客户端使用

1. 面板首页/订阅页复制订阅链接: `https://x3ui.<域名>:2096/sub/<subId>`
2. 客户端(v2rayN / Shadowrocket / Streisand 等)→ 订阅管理 → 添加该 URL → 更新
3. 选择节点连接; 客户端会随订阅自动更新节点增删

---

## 8. 运维

```sh
# 升级镜像
docker compose --env-file server-x3-ui/.env -f server-x3-ui/compose.yml pull 3x-ui
docker compose --env-file server-x3-ui/.env -f server-x3-ui/compose.yml up -d 3x-ui

# 备份(停容器后拷贝整个目录最稳妥)
tar czf x3-ui-backup-$(date +%F).tgz server-x3-ui/{db,cert,.env}

# 日志
docker logs -f --tail 100 3x-ui
```

迁移机器: 新机装好 Docker/Nginx → 还原 `db/ cert/ .env` → 重复本文 2.1/2.2/3 步。

---

## 9. 故障排查

| 现象 | 排查 |
| --- | --- |
| 面板打不开 | `curl -I http://127.0.0.1:2053` 通则查 Nginx; 再查 CF SSL 模式应为 Full |
| 订阅链接无法访问 | `docker logs 3x-ui \| grep -i sub`; 本机 `curl -k https://127.0.0.1:2096/` 验证 TLS |
| 节点不通(方案A) | ① 客户端地址是否绕开了 CF 代理域名 ② dest 目标站是否为微软系(换 `gateway.icloud.com`) ③ 端口/ufw/安全组 ④ 客户端 flow 是否 `xtls-rprx-vision` |
| 节点不通(方案B) | path 是否一致、nginx `/ws` 是否启用、CF 是否放行 WebSocket |
| 改了 .env 不生效 | 必须 `up -d --force-recreate`, restart 不会更新端口/env |
| Reality 握手被服务端关闭且无日志 | 打开入站 `show` 开关看认证判定; 用 `xray x25519 -i <私钥>` 核对公钥; 检查容器内到目标站的连通性 |
