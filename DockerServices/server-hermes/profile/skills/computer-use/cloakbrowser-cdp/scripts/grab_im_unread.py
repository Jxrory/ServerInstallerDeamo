#!/usr/bin/env python3
"""TikTok Partner Center IM 未读会话抓取（实测可用，2026-08）。

用法：改 BASE/TOKEN/PID（见记忆）+ UNREAD_NAMES（或先跑 probe 拿名单），
      cd /opt/data/cdp && .venv/bin/python grab_im_unread.py
前提：Profile 已登录 partner.us.tiktokshop.com，IM 页已打开过（复用页面状态，不重载）。
输出：/opt/data/cdp/im_unread.json —— {会话名: {header, count, messages: [{time, sender, type, content}]}}

关键坑（详见 references/tiktok-partner-im.md）：
- 会话卡片必须 locator.click() 真实点击；evaluate 原生 click 无效（右侧永远 "No chat selected."）
- 列表 ~25-30s 才加载完，轮询 body 文本出现 "Unread (N)" 再操作
- [class*="messageRow"] 会命中列表项，聊天消息只认 .chatd-message
"""
import asyncio, json
from playwright.async_api import async_playwright

BASE  = "http://cloakbrowser-manager:8080"
TOKEN = "<AUTH_TOKEN>"            # 见记忆
PID   = "<profile-id>"            # 见记忆
URL   = "https://partner.us.tiktokshop.com/partner/im?market=100&enter_from=ttspc_im_popup_entry"

UNREAD_NAMES = []  # 未读会话名单；留空则自动从列表收集（有未读角标的卡片）

async def grab_current_chat(page):
    """抓取当前打开的聊天窗内全部消息"""
    return await page.evaluate("""() => {
        const room = document.querySelector('[class*="chatRoom--"]') ||
                     document.querySelector('[class*="chatRoomContainer"]');
        if (!room) return {error: 'no chatRoom'};
        const header = room.querySelector('[class*="chatHeader"], [class*="header"]');
        const msgs = room.querySelectorAll('.chatd-message');
        const list = [];
        for (const m of msgs) {
            const cls = m.className || '';
            const isRight = cls.includes('chatd-message--right');
            const timeEl = m.querySelector('.chatd-time');
            const time = timeEl ? timeEl.textContent.trim() : '';
            const sysEl = m.querySelector('[class*="messageSystemContent"]');
            const bubble = m.querySelector('.chatd-bubble');
            const userNameEl = m.querySelector('.chatd-message-userName');
            const userName = userNameEl && !userNameEl.classList.contains('hide')
                ? userNameEl.textContent.trim() : '';
            let type = 'text', content = '';
            if (sysEl) { type = 'system'; content = sysEl.textContent.trim(); }
            else if (bubble) {
                const pre = bubble.querySelector('pre');
                content = pre ? pre.textContent.trim() : bubble.innerText.trim();
                const card = m.querySelector('.chatd-message-body-info-message [class*="w-["]');
                if (card && (card.innerText.includes('Invitation') || card.innerText.includes('product') || card.innerText.includes('$'))) {
                    type = 'card'; content = card.innerText.trim();
                }
                type = type + (isRight ? '_self' : '_other');
            } else {
                content = m.innerText.trim().slice(0, 200); type = 'other';
            }
            if (isRight && type === 'text') type = 'text_self';
            if (!isRight && type === 'text') type = 'text_other';
            list.push({time, sender: userName || (isRight ? 'Nice M(me)' : 'them'), type, content});
        }
        return {header: header ? header.innerText.trim().slice(0,80) : '', count: list.length, messages: list};
    }""")

async def collect_unread_names(page):
    return await page.evaluate("""() => {
        const names = [];
        document.querySelectorAll('.arco-list-item').forEach(li => {
            const b = li.querySelector('.m4b-badge-number');
            if (b && parseInt(b.textContent.trim()) > 0) {
                const lines = li.innerText.split('\\n').map(s=>s.trim()).filter(Boolean);
                // 行序: 未读数 | 名字 | ...
                if (lines.length > 1) names.push({name: lines[1], unread: parseInt(b.textContent.trim())});
            }
        });
        return names;
    }""")

async def click_card_by_name(page, name):
    cards = page.locator('[class*="contactCard"]')
    for i in range(await cards.count()):
        card = cards.nth(i)
        if name in (await card.inner_text()):
            await card.scroll_into_view_if_needed()
            await card.click(timeout=8000)
            return True
    return False

async def agent_task():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(
            f"{BASE}/api/profiles/{PID}/cdp",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=15000,
        )
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("current url:", page.url)

        # 复用页面：只在不在 IM 页时才导航
        if "partner/im" not in page.url:
            await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
            for _ in range(12):
                await page.wait_for_timeout(5000)
                if "Unread (" in await page.evaluate("document.body.innerText"):
                    break
        else:
            await page.wait_for_timeout(2000)

        names = UNREAD_NAMES or [n["name"] for n in await collect_unread_names(page)]
        print("targets:", names)

        results = {}
        for name in names:
            if not await click_card_by_name(page, name):
                results[name] = {"error": "card not found"}; print(f"[{name}] CARD NOT FOUND"); continue
            try:
                await page.wait_for_selector('.chatd-message', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(3500)
            data = await grab_current_chat(page)
            # header 为空是常态（选择器未匹配），以消息 sender/内容为准
            if data.get("count") == 0:
                await click_card_by_name(page, name); await page.wait_for_timeout(3500)
                data = await grab_current_chat(page)
            results[name] = data
            print(f"[{name}] msgs={data.get('count')}")

        out = "/opt/data/cdp/im_unread.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("saved", out)
        await browser.close()

asyncio.run(agent_task())
