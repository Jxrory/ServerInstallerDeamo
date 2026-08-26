你的架构可以设计成：

```
                 Internet
                    |
                  443
                    |
                 Nginx
                    |
          -------------------
          |                 |
       面板域名           节点端口
   panel.example.com       443/8443...
          |
       127.0.0.1:2053
          |
      Docker 3x-ui
          |
       Xray Core
          |
       宿主机网络
```

这种方式比较适合生产环境：**Docker 管理 3x-ui，宿主机 Nginx 做入口和 TLS，Xray 节点端口直接走宿主机。**

---

## 1. 目录规划

例如：

```bash
mkdir -p /opt/3x-ui/{db,cert}
cd /opt/3x-ui
```

结构：

```
/opt/3x-ui
├── compose.yml
├── db
└── cert
```

---

## 2. Docker Compose

`/opt/3x-ui/compose.yml`

```yaml
services:
  3x-ui:
    image: ghcr.io/mhsanaei/3x-ui:latest
    container_name: 3x-ui

    restart: unless-stopped

    ports:
      - "127.0.0.1:2053:2053"

    volumes:
      - ./db:/etc/x-ui
      - ./cert:/root/cert

    environment:
      XRAY_VMESS_AEAD_FORCED: "false"
      XUI_ENABLE_FAIL2BAN: "true"
```

这里重点：

```yaml
127.0.0.1:2053:2053
```

表示：

* Docker 暴露 2053
* 只允许宿主机访问
* 外网不能直接访问面板

---

启动：

```bash
docker compose up -d
```

检查：

```bash
docker ps
```

---

## 3. Nginx 反代面板

假设：

```
panel.example.com
```

DNS：

```
A记录

panel.example.com -> 服务器IP
```

安装：

```bash
apt install nginx certbot python3-certbot-nginx
```

创建：

```bash
nano /etc/nginx/conf.d/3x-ui.conf
```

内容：

```nginx
server {

    listen 80;

    server_name panel.example.com;


    location / {

        proxy_pass http://127.0.0.1:2053;


        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

测试：

```bash
nginx -t
```

重载：

```bash
systemctl reload nginx
```

---

## 4. 配置 HTTPS

执行：

```bash
certbot --nginx -d panel.example.com
```

成功后：

访问：

```
https://panel.example.com
```

---

## 5. Xray 节点端口怎么处理？

这里有一个关键点：

### 不建议：

```
Docker port mapping

443:443
```

因为：

* Nginx 会占 443
* Xray 也想占 443
* 会冲突

推荐：

### 方案 A（推荐）：Xray 使用宿主机端口

比如：

```
VLESS Reality

监听:
8443
```

客户端：

```
server.com:8443
```

compose 不需要开放：

```yaml
ports:
```

只需要 Xray 在容器内部监听，然后映射：

例如：

```yaml
ports:
  - "8443:8443"
```

---

## 6. 如果想 VLESS + WebSocket + Nginx 共用443

架构：

```
443
 |
 nginx
 |
 +---- panel.example.com
 |
 +---- cdn.example.com/ws
             |
          3x-ui/Xray
```

Nginx：

```nginx
location /ws {

    proxy_pass http://127.0.0.1:10000;

    proxy_http_version 1.1;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

Xray:

```
监听:
10000

path:
/ws
```

这种适合：

* VLESS WS TLS
* Trojan WS
* CDN

---

## 7. 推荐安全设置

### 修改后台路径

不要：

```
/panel
```

默认：

```
/
```

建议：

```
/a8f92kd/
```

例如：

```
https://panel.example.com/a8f92kd/
```

---

### 修改默认账号

进入：

```
Panel
 |
Settings
 |
Account
```

修改：

```
admin
```

---

### 防火墙

只开放：

```
80
443
节点端口
```

例如：

```bash
ufw allow 80
ufw allow 443
ufw allow 8443
```

关闭：

```
2053
```

---

## 8. 最终推荐架构

我会这样部署：

```
宿主机
|
├── Nginx
|    |
|    ├── panel.example.com
|    |       |
|    |    127.0.0.1:2053
|    |
|    └── node.example.com/ws
|
|
└── Docker
     |
     └── 3x-ui
          |
          └── Xray
```

优点：

* 面板不暴露公网
* HTTPS 统一管理
* Nginx 自动续证书
* Docker 易升级
* 后续迁移简单

这个方案也是目前生产环境部署 3x-ui 比较常见的方式。
