#!/usr/bin/env python3
"""TikTok Shop Partner Center 凭证采集 + 网关上传 一键脚本

流程: 连接 CloakBrowser → 确认登录 → 提取 Cookie → 导航两个页面提取 partner_id → POST 上传网关 → 验证 API
用法: .venv/bin/python collect_and_upload.py
依赖: playwright (uv venv cdp/.venv && uv pip install --python cdp/.venv/bin/python playwright)
"""
import asyncio, json, re, sys
from playwright.async_api import async_playwright

# ============ 配置 ============
BASE = "http://cloakbrowser-manager:8080"          # CloakBrowser Manager (容器内)
TOKEN = "ykkjEAWdaSdUk3VMlsY9zoxv4_KsgFPQa4nv2"    # Manager Bearer token
PID = "c485ff8d-d2b7-41f8-86f9-a993a5fde04c"       # TpaBrowser01
GATEWAY = "http://tk-gateway:8549"                 # 网关 (容器内, 不是公网域名!)
GATEWAY_KEY = "1f61EdaA5e353aFDdb42bef3Bd119eA1"   # X-API-Key
ACCOUNT_NAME = "Nice M - US Partner Center"
# =================================

HOME_URL = "https://partner.us.tiktokshop.com/home"
SAMPLES_URL = "https://partner.us.tiktokshop.com/affiliate-campaign/sample-requests?market=100&tab=to_review"
CREATORS_URL = "https://partner.us.tiktokshop.com/affiliate-cmp/creator?market=100"


async def connect(pw):
    browser = await pw.chromium.connect_over_cdp(
        f"{BASE}/api/profiles/{PID}/cdp",
        headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    return browser, ctx, page


async def ensure_logged_in(page):
    await page.goto(HOME_URL, timeout=45000, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    body = await page.locator("body").inner_text(timeout=10000)
    if "Welcome to TikTok Shop Partner Center" not in body:
        print("⚠️ 未检测到登录态, 请在浏览器中手动完成登录后重试")
        return False
    print("✅ 已登录 Partner Center")
    return True


async def extract_cookies(ctx):
    cookies = await ctx.cookies()
    required = ["sessionid", "sid_tt", "oec_lucifer", "msToken",
                "passport_csrf_token", "sessionid_ss", "ttwid"]
    names = {c["name"] for c in cookies}
    missing = [k for k in required if k not in names]
    if missing:
        print(f"⚠️ 缺少关键 cookie: {missing}")
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    print(f"✅ 提取 {len(cookies)} 个 cookie, 串长 {len(cookie_str)}")
    return cookie_str


async def capture_partner_id(page, url, label, path_hint):
    """导航到页面, 监听请求, 从 partner_id 参数提取"""
    captured = []
    page.on("request", lambda req: captured.append(req.url))
    await page.goto(url, timeout=45000, wait_until="domcontentloaded")
    await page.wait_for_timeout(10000)
    ids = set()
    for u in captured:
        if path_hint in u:
            m = re.search(r'partner_id=(\d+)', u)
            if m:
                ids.add(m.group(1))
    if len(ids) != 1:
        print(f"⚠️ {label}: 找到 {len(ids)} 个 partner_id ({ids}), 检查 path_hint={path_hint}")
    pid = ids.pop() if ids else None
    print(f"{'✅' if pid else '❌'} {label}: {pid}")
    return pid


async def upload_to_gateway(sample_pid, creator_pid, cookie_str):
    payload = {
        "name": ACCOUNT_NAME,
        "sample_partner_id": sample_pid,
        "creator_partner_id": creator_pid,
        "cookies": cookie_str,
    }
    import urllib.request
    req = urllib.request.Request(
        f"{GATEWAY}/api/v1/accounts",
        data=json.dumps(payload).encode(),
        headers={"X-API-Key": GATEWAY_KEY, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
            print(f"✅ 上传成功: {json.dumps(body, ensure_ascii=False)}")
            return body
    except urllib.error.HTTPError as e:
        print(f"❌ 上传失败 HTTP {e.code}: {e.read().decode()[:300]}")
        return None


async def verify_gateway(account_id):
    import urllib.request
    for label, path in [
        ("样品列表", f"/api/v1/accounts/{account_id}/samples?status=to_review"),
        ("达人列表", f"/api/v1/accounts/{account_id}/creators?query=&size=20"),
    ]:
        req = urllib.request.Request(f"{GATEWAY}{path}", headers={"X-API-Key": GATEWAY_KEY})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read())
                total = data.get("total", "?")
                print(f"✅ {label}: HTTP {resp.status}, total={total}")
        except urllib.error.HTTPError as e:
            print(f"❌ {label}: HTTP {e.code}: {e.read().decode()[:200]}")


async def main():
    async with async_playwright() as pw:
        browser, ctx, page = await connect(pw)
        try:
            if not await ensure_logged_in(page):
                return
            cookie_str = await extract_cookies(ctx)
            sample_pid = await capture_partner_id(
                page, SAMPLES_URL, "sample_partner_id", "/affiliate/partner/")
            creator_pid = await capture_partner_id(
                page, CREATORS_URL, "creator_partner_id", "/oec/affiliate/creator/marketplace/")
            if not (sample_pid and creator_pid):
                print("❌ partner_id 提取不完整, 中止上传")
                return
            result = await upload_to_gateway(sample_pid, creator_pid, cookie_str)
            if result:
                await verify_gateway(result.get("id"))
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
