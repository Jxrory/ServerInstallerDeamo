下面给你一份可以直接放在项目里的 **README.md（适配你这个 nginx 多服务部署脚本）**，已经按“生产可用 + 清晰说明 + 新手可执行”写好了。

---

# 📦 Nginx Multi-Service Installer

一个用于 **批量部署 Nginx 反向代理服务** 的自动化脚本工具，支持多服务配置、自动校验、失败阻断和安全部署。

---

## 📁 项目结构

```
.
├── conf/              # nginx site 配置目录（每个文件一个服务）
│   ├── chatwoot
│   ├── cs-agent
│   └── ...
├── ssl/              # SSL 证书目录（可选）
├── install.sh        # 一键部署脚本
└── README.md
```

---

## 🚀 功能特性

* ✅ 自动安装 nginx（如未安装）
* ✅ 自动部署多个 nginx site
* ✅ 支持任意数量服务（conf 目录驱动）
* ✅ 安全校验（nginx -t）
* ✅ 配置错误直接阻断，不会污染生产环境
* ✅ 幂等设计（可重复执行）
* ✅ 自动启用 sites-enabled
* ✅ 支持 UFW 防火墙端口开放（80 / 443）

---

## 📌 使用方法

### 1️⃣ 准备配置文件

在 `conf/` 目录下添加 nginx 配置文件，例如：

```
conf/chatwoot
```

示例内容：

```nginx
server {
    listen 80;
    server_name chat.example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 2️⃣ 赋予执行权限

```bash
chmod +x install.sh
```

---

### 3️⃣ 执行安装

```bash
./install.sh
```

---

## 🔐 安全机制

脚本会在部署前执行以下检查：

### ✔ nginx 配置预检

* 所有 conf 文件必须通过 nginx 语法检查
* 任意一个失败 → 整体终止部署

### ✔ 最终全局检查

* 所有配置安装后再次执行 `nginx -t`
* 确保不会破坏现有 nginx

---

## ❌ 配置错误处理机制

如果配置错误，脚本会：

* ❌ 显示具体错误信息
* ❌ 停止部署流程
* ❌ 不修改生产 nginx 配置
* ❌ 不 reload nginx

---

## 🔄 可重复执行（幂等）

你可以安全多次执行：

```bash
./install.sh
```

特点：

* 已存在 site 不会重复创建
* 不会重复添加配置
* 不会破坏已有服务

---

## 🌐 支持场景

适用于：

* Chatwoot
* Node.js / Express
* Python Flask / FastAPI
* Go web service
* Docker container reverse proxy
* 任意 HTTP backend

---

## 📦 示例：多服务部署

```
conf/
 ├── chatwoot      -> chat.example.com
 ├── cs-agent      -> agent.example.com
 ├── api           -> api.example.com
```

---

## 🔧 常见问题

### ❓ nginx 配置失败怎么办？

运行：

```bash
sudo nginx -t
```

根据报错修复对应 conf 文件。

---

### ❓ 如何新增服务？

只需要：

1. 在 `conf/` 里新增文件
2. 重新运行：

```bash
./install.sh
```

---

## 🧠 设计理念

这个工具的核心原则：

> “配置驱动部署，而不是脚本写死服务”

---
