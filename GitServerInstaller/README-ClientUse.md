
* 生成 SSH 密钥对
* 添加到 Git Server
* 配置 SSH config（免写 IP / 端口）
* 验证连接

---

# 🔐 Git Server 客户端 SSH 配置指南

---

# 1️⃣ 生成 SSH 密钥对

在**客户端（你的开发机器）执行：**

```bash id="k3p9qa"
mkdir -p ~/.ssh/git

ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ~/.ssh/git/git_server
```

---

## ✔ 交互说明

系统会提示：

```text
Enter file in which to save the key (/home/user/.ssh/git/git_server):
```

👉 直接回车（使用默认路径）

```text
Enter passphrase (empty for no passphrase):
```

👉 可以：

* 直接回车（免密，方便但安全性一般）
* 或设置密码（更安全）

---

## ✔ 生成结果

默认生成两个文件：

```text
~/.ssh/git/git_server        # 私钥（不要泄露）
~/.ssh/git/git_server.pub    # 公钥（要上传服务器）
```

---

# 2️⃣ 将公钥添加到 Git Server

## ✔ 方法一：自动上传（推荐）

```bash id="x8f7sd"
ssh-copy-id -i ~/.ssh/git/git_server.pub git@服务器IP
```

如果 SSH 端口不是 22：

```bash id="q7m2kc"
ssh-copy-id -p 7700 -i ~/.ssh/git/git_server.pub git@服务器IP
```

---

## ✔ 方法二：手动添加

查看公钥：

```bash id="p4kq1n"
cat ~/.ssh/git/git_server.pub
```

复制内容，登录服务器：

```bash id="v9lq7a"
ssh git@服务器IP
```

编辑文件：

```bash id="c8n2sb"
vim ~/.ssh/authorized_keys
```

粘贴进去（每行一个 key）

---

## ✔ 修复权限（服务器端必须执行）

```bash id="m5zq1p"
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chown -R git:git ~/.ssh
```

---

# 3️⃣ 配置 SSH config（强烈推荐）

这样你以后就不用写 IP / 端口了。

编辑客户端：

```bash id="n7xq2v"
vim ~/.ssh/config
```

---

## ✔ 基础配置（默认 22 端口）

```conf id="t9wq3k"
Host git-server
    HostName 192.168.1.100
    User git
    IdentityFile ~/.ssh/git/git_server
```

---

## ✔ 如果 SSH 端口不是 22（例如 7700）

```conf id="k2v9pm"
Host git-server
    HostName 192.168.1.100
    User git
    Port 7700
    IdentityFile ~/.ssh/git/git_server
```

---

## ✔ 权限设置（必须）

```bash id="h3q8sd"
chmod 600 ~/.ssh/config
```

---

# 4️⃣ 测试 SSH 连接

```bash id="z7m2lk"
ssh git-server
```

如果成功，你会看到：

```text
Welcome to Ubuntu...
```

或者直接进入 git-shell（正常现象）

---

# 5️⃣ 使用 Git 克隆仓库

## ✔ 使用 SSH config 别名（推荐）

```bash id="w4kq1p"
git clone git-server:repo/test.git
```

---

# 🚀 推荐最佳实践（很重要）

## ✔ 1. 一个用户一把 key

不要多人共用 `git` 私钥

## ✔ 2. 禁止密码登录 git 用户

配合你前面那篇：

```bash
PasswordAuthentication no
```

## ✔ 3. 用 config 管理多服务器

```conf
Host prod-git
Host staging-git
Host dev-git
```

---
