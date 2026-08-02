---
name: tiktok-partner-im
description: 抓取 TikTok Shop Partner Center 站内信 IM（partner.us.tiktokshop.com/partner/im）的会话列表与未读消息历史。通过已登录的 CloakBrowser Profile 走 CDP，识别 chatd 组件结构，逐个真实点开会话提取完整聊天记录（时间/发送方/文本/系统提示/合作邀请卡片）。用于达人合作消息监控、未读消息批量读取。依赖 cloakbrowser-cdp 技能的连接方式。
---

# TikTok Partner Center IM 抓取（实测验证版）

场景：读取 TikTok Shop Partner Center 站内信（IM）的未读会话和聊天历史。已在本环境实测，11 个未读会话 / 45 条消息完整抓取。

## 触发条件

- 需要读 IM 会话列表、未读消息、聊天历史（如达人合作消息监控）
- 目标 URL: `https://partner.us.tiktokshop.com/partner/im?market=100&enter_from=ttspc_im_popup_entry`

## 前置

- CloakBrowser Profile 已登录 partner.us.tiktokshop.com（本环境账号 'Nice M'，PID/TOKEN 见记忆）
- 连接方式完全复用 `cloakbrowser-cdp` skill：`connect_over_cdp` + Bearer header（WS 握手也要带）
- Playwright venv: `/opt/data/cdp/.venv`；脚本模板 `scripts/im_grab.py`

## 核心步骤

1. **连接 CDP**（Bearer 认证）
2. **不要每次 goto**：该页加载极慢（列表 25-30s 才出现）。先检查 `page.url` 是否已在 `/partner/im`，是则直接复用页面状态，只 `wait_for_timeout` 等数据
3. **等列表**：`body.innerText` 含 `Unread (N)` 即加载完成（N>0 表示有待读）
4. **抓会话列表**：`.arco-list-item` 内 `[class*="contactCard"]`；未读角标 `.m4b-badge-number`（All 视图是 1000+ 虚拟列表，首屏约 15 项，未读会话都在首屏）
5. **必须真实点击**：用 `locator.click()`（Playwright 合成输入事件）点卡片才打开会话；`evaluate` 里 `element.click()` **无效**，右侧会一直显示 "No chat selected."
6. **抓消息**：等 `.chatd-message` 出现后，限定在 chatRoom 内提取

## chatd 组件 DOM 结构（TikTok 自研 IM SDK）

- 消息容器：`.chatd-message`
  - `.chatd-message--right` = 我方（账号名）
  - `.chatd-message--left` = 对方
  - `.chatd-message--hasTime` = 该条带时间
- 时间：`.chatd-message-time > time.chatd-time`（无则空字符串）
- 发送者：`.chatd-message-userName`（class 含 `hide` 时不显示）
- 内容分类：
  - 文本气泡：`.chatd-bubble`（`--self` 我方 / `--other` 对方），正文在 `pre` 里
  - 系统提示（如 "N products added to showcase"）：`[class*="messageSystemContent"]`
  - 合作邀请卡片（"Invitation to Collaborate" + 产品数 + 价格 $x.xx）：`.chatd-message-body-info-message` 内 `[class*="w-["]` 容器，取 `innerText`

## 脚本

`scripts/im_grab.py` —— 完整流程：复用页面 → 自动发现未读会话 → 逐个真实点击 → 抓消息 → 存 JSON。

```bash
cd /opt/data/cdp && CBM_TOKEN=<token> CBM_PID=<profile-id> .venv/bin/python im_grab.py [输出.json] [会话名过滤,逗号分隔]
# 默认输出 /opt/data/cdp/im_unread.json；不带过滤 = 抓全部未读会话
```

输出 JSON 结构：`{会话名: {count, messages: [{time, sender, type, content}]}}`
- type: `text_self`（我方文本）/ `text_other`（对方文本）/ `system`（系统提示）/ `card_self` / `card_other`（邀请卡片）
- sender: 对方用户名 或 `Nice M(me)`

## 坑（实测踩过）

1. 页面加载 25-30s+，脚本间务必复用页面，别反复 goto/reload（网络慢会雪上加霜）
2. `element.click()` 无效 → 一律 `locator.click()`，必要时先 `scroll_into_view_if_needed()`
3. 卡片 `innerText` 行结构：`[未读数字, 名字, "Not replied"?, 时间, 预览]` —— 匹配名字用 `in` 包含判断，别取第一行
4. chatRoom 容器同时含左侧列表 + 右侧聊天窗，消息选择器必须用聊天窗专用类 `.chatd-message`，别用宽泛的 `[class*="message"]`（会抓到列表预览）
5. 点击会话会把未读角标清零（正常行为）；页面标题 "Messages (N new)" 的 N 是未读消息总数
6. 超 365 天的消息不可见（"Messages older than 365 days are not available."）
7. 系统提示消息（showcase 增删产品）sender 显示 `them`，但实际是对方操作事件，不是文本消息

## 验证

- 脚本输出每个会话 `msgs=N` 且无 `CARD NOT FOUND`
- JSON 每条消息含 time / sender / type / content 四字段
- 抽查：会话历史第一条通常是邀请卡片（`Invitation to Collaborate`），最后一条应是列表预览对应的那条消息
