---
name: cloakbrowser-cdp
description: Drive CloakBrowser-managed browser profiles over CDP with Playwright — connect_over_cdp with Bearer auth, navigate, locate/fill/click, inject JS via evaluate, iframes, popups, screenshots. Use when a task needs programmatic control of the running CloakBrowser profile (form automation, login flows, scraping, UI verification) or when the user mentions cloakbrowser-manager / CDP / Profile.
---

# CloakBrowser CDP 驱动（实测验证版）

场景：AI agent 通过 CloakBrowser-Manager 的 CDP 代理程序化操作运行中的浏览器 Profile。本 skill 内容已在本环境实测（17/17 断言通过）。

## 环境事实（本环境实测）

- Manager 与本 Hermes 容器同处 Docker 网络：`BASE=http://cloakbrowser-manager:8080`（容器内视角，唯一可用入口）
- ⚠️ 旧文档 §12 模板的 `http://127.0.0.1:2526`（宿主机视角）在容器内**不通**（HTTP 000），只在 Docker 宿主机上有效
- 认证：`Authorization: Bearer <TOKEN>`；无 token → 401。Token/Profile ID 见记忆或 `curl -s $BASE/api/profiles -H "Authorization: Bearer $TOKEN"`
- CDP 端点：`GET $BASE/api/profiles/<id>/cdp` 返回 JSON（含 usage 提示），HTTP URL 直接喂 `connect_over_cdp`
- Playwright venv（已装好，无需下载浏览器二进制）：`/opt/data/cdp/.venv`
- 本地测试页：`http://172.22.0.3:8899/index.html`（浏览器容器同网段 IP 可达；`host.docker.internal` 本环境只解析出 IPv6、宿主机 8899 未起，不可依赖）
- 本容器 IP `172.22.0.3`；浏览器在另一个容器，访问本容器服务一律用 `http://172.22.0.3:<port>`

## 核心流程：连接 → 读 → 决策 → 操作 → 验证 → 断开

```python
import asyncio
from playwright.async_api import async_playwright

BASE  = "http://cloakbrowser-manager:8080"   # 容器内视角（不是 127.0.0.1:2526！）
TOKEN = "<AUTH_TOKEN>"
PID   = "<profile-id>"                       # 从 GET /api/profiles 拿

async def agent_task():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(
            f"{BASE}/api/profiles/{PID}/cdp",
            headers={"Authorization": f"Bearer {TOKEN}"},  # ★ WS 握手也要认证
            timeout=15000,
        )
        ctx = browser.contexts[0]             # Profile 持久化上下文：cookie/localStorage 都在
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # 1) 导航
        await page.goto("https://target.site", timeout=30000)
        await page.wait_for_load_state("domcontentloaded")

        # 2) 读页面（agent 理解现状）
        body = await page.locator("body").inner_text()
        print("页面现状:", body[:200].replace("\n", " "))

        # 3) 操作：语义化定位 + 填表 + 点击
        await page.fill("#username", "agent_user")          # 中文/特殊字符 OK
        await page.get_by_role("button", name="登录").click()

        # 4) 验证（不靠猜时间）
        await page.wait_for_selector("#result:has-text('submitted')", timeout=5000)
        print("结果:", await page.locator("#result").text_content())
        await page.screenshot(path="/tmp/evidence.png")

        await browser.close()   # 只断开 CDP；Profile 保持运行（noVNC 不中断）

asyncio.run(agent_task())
```

## 关键 API 速查

- **定位**：`page.get_by_role("button", name=...)`（最稳）> `get_by_text` / `get_by_placeholder` > CSS `locator("#id")` > XPath 兜底；链式 `locator("div.card >> text=立即购买")`
- **evaluate 四形态**：① 读值 `page.evaluate("document.title")`；② 多行箭头函数改 DOM/设全局；③ 传参 `page.evaluate("([k,v]) => localStorage.setItem(k,v)", ["k","v"])`；④ 返回结构化数据（如 `Array.from(document.querySelectorAll('input')).map(...)`）
- **init_script 持久化**：`await ctx.add_init_script("window.__flag = 1")` 后续所有导航都先执行（拦截 XHR、隐藏弹层）
- **iframe**：`page.frame_locator("#login-frame").locator("#inner-input").fill(...)`；嵌套 `.frame_locator("#outer").frame_locator("#inner")`
- **新窗口**：`async with page.expect_popup() as p: await page.locator(...).click()`；popup 需 `await p.value.wait_for_load_state()` 再操作
- **键盘**：`page.keyboard.press("Control+A")` / `type()`；防输入法站点用 `fill()`
- **截图**：`page.screenshot(path=..., full_page=True)` / 元素截图 `locator.screenshot(...)`
- **表格提取**：`page.evaluate` 遍历 `table tr` → JSON（见 scripts/test_cdp.py 示例）

## 验证

```bash
cd /opt/data/cdp && .venv/bin/python test_cdp.py   # 期望 17/17 PASS
```

skill 自带副本：`scripts/test_cdp.py` + `templates/testpage/`（index/frame/popup.html，含表单、iframe、弹窗、计数器，可起 `python3 -m http.server 8899 --bind 0.0.0.0` 复测）。

## 坑（实测踩过）

1. 容器内 BASE 用 `cloakbrowser-manager:8080`；`127.0.0.1:2526` 是宿主机视角，容器内 000
2. WS 握手必须带 Bearer header，漏掉 → 401 拒连
3. `networkidle` 在 SPA/埋点页永不触发 → 用 `wait_for_selector` 等业务元素
4. 元素找不到 → 先查是否在 iframe（换 `frame_locator`）/ Shadow DOM（evaluate 穿透）/ 另一个标签页（遍历 `ctx.pages`）
5. 点击无反应 → `scroll_into_view_if_needed()` 或 `force=True`，事件绑父级则 evaluate 触发
6. 页面跳转后 locator 失效（StaleElement）→ 重新查询，别缓存 locator
7. 中文输入用 `fill()` 最稳；`type()`/`press_sequentially` 走键盘事件，个别站点会丢
8. `window.open` 新页未加载完就操作会报错 → 先 `wait_for_load_state()`
9. `browser.close()` 只断连；彻底停浏览器用 `POST /api/profiles/{id}/stop`，别直接杀进程（留锁文件/僵尸 VNC）
10. 反爬校验：`navigator.webdriver` 应为 false；强风控开 `headless: false` + `humanize: true`（Profile 配置）

## 参考

- 主文档：`cloakbrowser-manager-usage.md`（架构 / API / 认证 / Profile 字段）
- Playwright Locator: https://playwright.dev/python/docs/locators
- Playwright Page API: https://playwright.dev/python/docs/api/class-page
- CloakBrowser: https://github.com/CloakHQ/CloakBrowser
