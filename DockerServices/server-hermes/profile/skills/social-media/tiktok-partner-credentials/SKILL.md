---
name: tiktok-partner-credentials
description: 采集 TikTok Shop Partner Center 登录凭证(cookie + 两个 partner_id)并上传到 TkGatewayService 网关。用 CloakBrowser CDP 连接已登录浏览器,从 context.cookies() 提取完整 cookie 串,监听网络请求从页面 API 提取 sample_partner_id 与 creator_partner_id,POST 到网关 /api/v1/accounts。适用于达人运营/样品管理数据采集场景。
---

# TikTok Shop Partner Center 凭证采集与网关上传

## 触发场景

- 需要把 TikTok Shop 账号凭证(登录态)接入 TkGatewayService 网关
- 网关账号过期(expired)后重新上传凭证
- 需要 sample_partner_id / creator_partner_id 调用网关数据 API

## 环境事实(本环境实测)

- CloakBrowser Manager: 容器内 `http://cloakbrowser-manager:8080`(外部域名 `https://cloak-browser.makemoney2g.com` 也可用,但容器内用短名最稳)
- Manager 认证: `POST /api/auth/login {"token": "<TOKEN>"}` 或直接 `Authorization: Bearer <TOKEN>`
- 浏览器 profile: `c485ff8d-d2b7-41f8-86f9-a993a5fde04c` (TpaBrowser01, headless=false, 已登录 Nice M 账号)
- ⚠️ 网关不在公网 HTTP 上: 外部域名 `tk-gateway.makemoney2g.com` 经 Cloudflare 301→HTTPS,且容器无对外端口;实际服务在**容器内 `http://tk-gateway:8549`**
- 网关 API key: header `X-API-Key: 1f61EdaA5e353aFDdb42bef3Bd119eA1`(env: `GATEWAY_API_KEY`)
- Playwright venv: `/opt/data/cdp/.venv`(若不存在: `cd /opt/data && uv venv cdp/.venv && uv pip install --python cdp/.venv/bin/python playwright`)
- Manager token / 网关 key 存于记忆,不必重复询问
- 一键脚本: `/opt/data/cdp/collect_and_upload.py`(完整流程,幂等可重复跑)

## 核心流程

### 1. 连接浏览器并确认登录态

```python
import asyncio
from playwright.async_api import async_playwright

BASE = "http://cloakbrowser-manager:8080"
TOKEN = "<manager token>"
PID   = "c485ff8d-d2b7-41f8-86f9-a993a5fde04c"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(
            f"{BASE}/api/profiles/{PID}/cdp",
            headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15000)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://partner.us.tiktokshop.com/home", timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        body = await page.locator("body").inner_text(timeout=10000)
        # 页面含 "Welcome to TikTok Shop Partner Center" 且导航栏可见 = 已登录
        print(body[:400])
        await browser.close()

asyncio.run(main())
```

未登录时先走登录流程(邮箱/密码或扫码),登录态持久化在 profile 中。

### 2. 提取完整 Cookie 串

用 `ctx.cookies()` 而非 F12 手动复制:

```python
cookies = await ctx.cookies()
cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
# 校验关键 cookie 齐全:
for k in ["sessionid", "sid_tt", "oec_lucifer", "msToken", "passport_csrf_token", "sessionid_ss", "ttwid"]:
    assert any(c["name"] == k for c in cookies), f"missing {k}"
```

### 3. 提取两个 partner_id(关键步骤)

导航到目标页面后**监听网络请求**,从请求 URL 的 `partner_id` 参数提取(比页面 URL 可靠,页面 URL 常不带 partner_id):

- **sample_partner_id**: 进入 `Creator Management -> Manage samples`(URL: `/affiliate-campaign/sample-requests`),刷新页面,捕获形如 `/api/v1/affiliate/partner/*?...partner_id=8667434091362813713...` 的请求
- **creator_partner_id**: 进入 `Creator Management -> Find creators`(URL: `/affiliate-cmp/creator`),捕获形如 `/api/v1/oec/affiliate/creator/marketplace/*?...partner_id=8667381864053704465...` 的请求

```python
captured = []
page.on("request", lambda req: captured.append(req.url))
await page.goto(url, timeout=45000, wait_until="domcontentloaded")
await page.wait_for_timeout(10000)
import re
ids = set()
for u in captured:
    if path_hint in u:  # "/affiliate/partner/" 或 "/oec/affiliate/creator/marketplace/"
        m = re.search(r'partner_id=(\d+)', u)
        if m: ids.add(m.group(1))
# 两个 id 不同! 用 API path 区分: affiliate/partner → sample; oec/affiliate/creator/marketplace → creator
```

侧边栏菜单是 JS 渲染的,无 `<a>` 标签,用 `page.get_by_text("Manage samples", exact=True).click()` 点击。

### 4. 上传凭证到网关

```bash
curl -X POST "http://tk-gateway:8549/api/v1/accounts" \
  -H "X-API-Key: $GATEWAY_API_KEY" -H "Content-Type: application/json" \
  --data @payload.json
# payload: {"name": "...", "sample_partner_id": "...", "creator_partner_id": "...", "cookies": "<完整 cookie 串>"}
# 成功: {"id":N, "status":"active"} HTTP 200
```

### 5. 验证网关 API

```bash
# 样品列表 (GET 仅对数据端点有效)
curl "http://tk-gateway:8549/api/v1/accounts/<id>/samples?status=to_review" -H "X-API-Key: $KEY"
# 达人列表
curl "http://tk-gateway:8549/api/v1/accounts/<id>/creators?query=&size=20" -H "X-API-Key: $KEY"
# 达人详情
curl "http://tk-gateway:8549/api/v1/accounts/<id>/creators/<oec_id>" -H "X-API-Key: $KEY"
```

## 坑(实测踩过)

1. **`GET /api/v1/accounts` 返回 401 "Invalid or missing API key" 是假象!** 该端点只允许 POST,GET 返回 405 才说明 key 已通过认证。验证 key 用 POST 建账号或请求数据端点,别用 GET 列表端点判断
2. 网关地址必须是容器内 `http://tk-gateway:8549`,外部 `https://tk-gateway.makemoney2g.com` 走 Cloudflare 且 8549 端口不通;`/health` 无需认证可先测连通
3. 技能 `cloakbrowser-cdp` 旧文档写 `cloakbrowser-manager:8080` 是 Manager;网关是**另一个服务**(tk-gateway 容器,8549),不要混淆
4. 两个 partner_id 不同且必须从对应页面 API 分别提取,不能混用(用请求 path 区分)
5. cookie 有时效,过期后网关自动标记 expired;重传时先 `ctx.cookies()` 重新提取(浏览器可能已刷新部分 token)
6. `networkidle` 在 SPA 不触发,等业务元素/固定延时;goto 后等 8-12s 让 API 请求发完
7. 侧边栏菜单无 `<a>` 标签,`get_by_text` 点击;菜单展开后子项才可见
8. 创建账号是**幂等/覆盖**行为:同名重复 POST 返回同一 id,无需先删旧账号

## 验证

- 网关返回 `status: active`
- `GET /accounts/<id>/creators?size=20` 返回 total=20 且含真实达人数据
- `GET /accounts/<id>/samples?status=to_review` 返回 total=0(空列表正常)

## 参考

- 网关 API 指南原文: `/opt/data/pastes/paste_1_154115.txt`
- CloakBrowser CDP 驱动细节: 技能 `cloakbrowser-cdp`
- 一键脚本: `/opt/data/cdp/collect_and_upload.py`
