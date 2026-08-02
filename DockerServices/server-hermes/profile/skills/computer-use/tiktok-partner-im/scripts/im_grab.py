#!/usr/bin/env python3
"""
TikTok Partner Center IM 抓取脚本（配合 cloakbrowser-cdp 使用）
- 复用已加载页面（不反复 goto，页面加载很慢）
- 自动发现未读会话（角标>0），逐个真实点击抓取完整历史
- 输出 JSON: {会话名: {count, messages: [{time, sender, type, content}]}}

用法:
  .venv/bin/python im_grab.py [输出路径] [会话名过滤,逗号分隔]
  CBM_TOKEN / CBM_PID 环境变量必填（见记忆）
示例:
  CBM_TOKEN=xxx CBM_PID=yyy .venv/bin/python im_grab.py
  CBM_TOKEN=xxx CBM_PID=yyy .venv/bin/python im_grab.py /tmp/im.json ladyang,milenaleon430
"""
import asyncio, json, sys, os
from playwright.async_api import async_playwright

BASE  = os.environ.get("CBM_BASE", "http://cloakbrowser-manager:8080")
TOKEN = os.environ.get("CBM_TOKEN", "")
PID   = os.environ.get("CBM_PID", "")

IM_URL = "https://partner.us.tiktokshop.com/partner/im?market=100&enter_from=ttspc_im_popup_entry"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/cdp/im_unread.json"
NAME_FILTER = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None


async def grab_current_chat(page):
    """抓取当前打开的聊天窗内全部消息（chatd 组件）"""
    return await page.evaluate("""() => {
        const room = document.querySelector('[class*="chatRoom--"]') ||
                     document.querySelector('[class*="chatRoomContainer"]');
        if (!room) return {error: 'no chatRoom'};
        const msgs = room.querySelectorAll('.chatd-message');
        const list = [];
        for (const m of msgs) {
            const cls = m.className || '';
            const isRight = cls.includes('chatd-message--right');
            const isLeft = cls.includes('chatd-message--left');
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
                content = m.innerText.trim().slice(0, 300);
                type = 'other';
            }
            if (isRight && type === 'text') type = 'text_self';
            if (isLeft && type === 'text') type = 'text_other';
            list.push({time, sender: userName || (isRight ? 'Nice M(me)' : 'them'), type, content});
        }
        return {count: list.length, messages: list};
    }""")


async def click_conversation(page, name):
    """按名字真实点击会话卡片（element.click() 无效，必须 locator.click()）"""
    cards = page.locator('[class*="contactCard"]')
    n = await cards.count()
    for i in range(n):
        card = cards.nth(i)
        txt = await card.inner_text()
        if name in txt:
            try:
                await card.scroll_into_view_if_needed()
            except Exception:
                pass
            await card.click(timeout=8000)
            return True
    return False


async def agent_task():
    if not TOKEN or not PID:
        print("ERROR: set CBM_TOKEN / CBM_PID env vars (see memory)")
        return
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(
            f"{BASE}/api/profiles/{PID}/cdp",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=15000,
        )
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("current url:", page.url)

        # 1) 只在不在 IM 页时才导航（页面加载 25-30s，勿反复 goto）
        if "partner/im" not in page.url:
            print("navigating to IM page...")
            await page.goto(IM_URL, timeout=90000, wait_until="domcontentloaded")
            for _ in range(14):
                await page.wait_for_timeout(5000)
                t = await page.evaluate("document.body.innerText")
                if "Unread (" in t:
                    break
        await page.wait_for_timeout(2000)

        # 2) 收集未读会话名（角标>0；卡片文本行 = [数字, 名字, ...]）
        unread = await page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.arco-list-item').forEach(li => {
                const badge = li.querySelector('.m4b-badge-number');
                const card = li.querySelector('[class*="contactCard"]');
                if (!card) return;
                const lines = card.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                if (badge && parseInt(badge.textContent.trim()) > 0) {
                    const name = lines[1] || lines[0];
                    out.push({name, unread: parseInt(badge.textContent.trim())});
                }
            });
            return out;
        }""")
        print("unread conversations:", json.dumps(unread, ensure_ascii=False))
        targets = [u["name"] for u in unread]
        if NAME_FILTER:
            targets = [n for n in targets if n in NAME_FILTER]
        if not targets:
            print("no unread conversations found (or filter matched none)")
            await browser.close()
            return

        # 3) 逐个打开并抓取
        results = {}
        for name in targets:
            if not await click_conversation(page, name):
                results[name] = {"error": "card not found"}
                print(f"[{name}] CARD NOT FOUND")
                continue
            try:
                await page.wait_for_selector('.chatd-message', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(3000)
            results[name] = await grab_current_chat(page)
            print(f"[{name}] msgs={results[name].get('count')}")

        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"saved -> {OUT}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(agent_task())
