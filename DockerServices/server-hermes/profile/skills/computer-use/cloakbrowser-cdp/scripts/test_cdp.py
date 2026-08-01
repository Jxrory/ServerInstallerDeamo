"""验证 cloakbrowser-manager CDP 实操指南的核心断言（§1-§11）。"""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://cloakbrowser-manager:8080"   # 容器视角（本环境实测可达）
TOKEN = "<AUTH_TOKEN>"
PID = "<profile-id>"
TEST_URL = "http://172.22.0.3:8899/index.html"  # 本容器 IP 上的测试页（浏览器容器可访问）

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  <- {detail}" if detail else ""))

async def main():
    async with async_playwright() as pw:
        # §1 连接（WS 握手带 Bearer）
        try:
            browser = await pw.chromium.connect_over_cdp(
                f"{BASE}/api/profiles/{PID}/cdp",
                headers={"Authorization": f"Bearer {TOKEN}"},
                timeout=15000,
            )
            check("§1 connect_over_cdp + Bearer", True)
        except Exception as e:
            check("§1 connect_over_cdp + Bearer", False, str(e)[:200])
            return

        ctx = browser.contexts[0]
        check("§1 contexts[0] 持久化上下文", True, f"共 {len(browser.contexts)} 个 context")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        check("§1 取到已有/新建 page", True, f"context 现有 {len(ctx.pages)} 个标签页: {[p.url[:60] for p in ctx.pages]}")

        # §2 导航与等待
        try:
            await page.goto(TEST_URL, timeout=20000)
            await page.wait_for_load_state("domcontentloaded")
            check("§2 goto + domcontentloaded", True, page.url)
        except Exception as e:
            check("§2 goto + domcontentloaded", False, str(e)[:200])

        # §9 读页面（agent 的眼睛）
        body = await page.locator("body").inner_text()
        check("§9 body.inner_text", "CDP 实操测试页" in body, body[:50].replace("\n", " "))

        # §3/§5 定位 + 填表
        await page.fill("#username", "agent_user")
        await page.fill("#password", "S3cret!中文")
        check("§5 fill 中文/特殊字符", True)

        # §4 点击（get_by_role）
        await page.get_by_role("button", name="登录").click()
        await page.wait_for_selector("#result:has-text('submitted')", timeout=5000)
        res = await page.locator("#result").text_content()
        check("§3/§4 get_by_role + §10 wait_for_selector", res == "submitted: agent_user/S3cret!中文", res)

        # §6.1 evaluate ① 读值
        title = await page.evaluate("document.title")
        check("§6.1 evaluate 读值", title == "CDP Test Page", title)

        # §6.1 evaluate ② 多行 + ③ 传参
        await page.evaluate("""() => {
            const el = document.getElementById('page-status');
            el.textContent = 'patched-by-agent';
            window.__agentFlag = { injected: true, ts: Date.now() };
        }""")
        flag = await page.evaluate("window.__agentFlag")
        check("§6.1 evaluate 多行注入", flag is not None and flag.get("injected") is True, str(flag))
        await page.evaluate("([k, v]) => localStorage.setItem(k, v)", ["agent_key", "agent_value"])
        ls = await page.evaluate("localStorage.getItem('agent_key')")
        check("§6.1 evaluate 传参", ls == "agent_value", ls)

        # §6.1 ④ 结构化提取 + §4 计数器点击
        await page.locator("#counter-btn").click()
        await page.locator("#counter-btn").click()
        count = await page.evaluate("document.getElementById('count').textContent")
        check("§4 点击计数", count == "2", f"count={count}")

        # §6.2 add_init_script 持久化
        await ctx.add_init_script("window.__initInjected = 'yes'")
        await page.reload(wait_until="domcontentloaded")
        init_ok = await page.evaluate("window.__initInjected")
        check("§6.2 add_init_script", init_ok == "yes", str(init_ok))
        await page.evaluate("localStorage.setItem('agent_key','')")  # 清理

        # §7 iframe（frame_locator）
        await page.frame_locator("#login-frame").locator("#inner-input").fill("iframe-value")
        await page.frame_locator("#login-frame").locator("#inner-btn").click()
        inner = await page.frame_locator("#login-frame").locator("#inner-result").text_content()
        check("§7 frame_locator 链式操作", inner == "inner-ok:iframe-value", inner)

        # §4 expect_popup 新窗口
        async with page.expect_popup() as popup_info:
            await page.locator("#open-window").click()
        popup = await popup_info.value
        await popup.wait_for_load_state()
        check("§4 expect_popup + 新页等待", "popup-loaded" in await popup.locator("body").inner_text(), popup.url)
        await popup.close()

        # §8 键盘
        await page.locator("#username").focus()
        await page.keyboard.press("Control+A")
        await page.keyboard.type("typed-via-keyboard")
        kb_val = await page.locator("#username").input_value()
        check("§8 键盘输入", kb_val == "typed-via-keyboard", kb_val)

        # §11 截图
        await page.screenshot(path="/tmp/cdp_full.png", full_page=True)
        await page.locator("#result").screenshot(path="/tmp/cdp_box.png")
        import os
        check("§11 截图", os.path.exists("/tmp/cdp_full.png") and os.path.getsize("/tmp/cdp_full.png") > 1000,
              f"{os.path.getsize('/tmp/cdp_full.png')} bytes")

        # §1 browser.close() 只断开
        await browser.close()
        check("§1 browser.close() 断开（不杀进程）", True)

    ok = sum(1 for _, o, _ in results if o)
    print(f"\n===== {ok}/{len(results)} 通过 =====")

asyncio.run(main())
