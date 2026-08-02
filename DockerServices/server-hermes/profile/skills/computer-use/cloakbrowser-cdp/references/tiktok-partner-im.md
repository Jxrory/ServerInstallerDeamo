# TikTok Partner Center IM 未读消息抓取（实测配方）

目标：读取 `https://partner.us.tiktokshop.com/partner/im?market=100&enter_from=ttspc_im_popup_entry` 的未读会话及完整历史。
前提：CloakBrowser Profile 已登录 partner.us.tiktokshop.com（实测账号 'Nice M'，Profile 见记忆）。
实测：11 个未读会话 / 16 条新消息 / 45 条历史消息一次抓全（2026-08 环境）。

## 页面加载特征（网络慢！）

- 列表约 **25-30s** 才出现：计数先显示 `All (0) / Unread (0)`，加载完成变成 `All (1000) / Unread (11)`。
- 等待方式：轮询 `document.body.innerText` 出现 `Unread (N)`（N>0）即完成，别 sleep 固定时长。
- 页面 title 会更新为 `Messages (16 new)`（16 = 未读消息总数，跨会话合计）。
- ⚠️ **复用页面状态**：脚本连接后先检查 `page.url`，已在 `/partner/im` 就直接操作，**不要 goto 重载**（用户明确要求：网络慢，重载一次 30s+ 太浪费）。

## 会话列表（左侧，宽 ~280px）

- 列表容器：`.arco-list`（虚拟列表 `arco-list-virtual`；All 有 1000 个会话，只渲染可见项）。
- 会话卡片：`.arco-list-item` 内 `[class*="contactCard"]`；卡片文本行序：`未读数 | 名字 | Not replied? | 时间 | 最后消息预览`。
- 未读角标：`.m4b-badge-number.m4b-badge-status-negative`（数字 = 该会话未读条数）。
- 过滤 tab：`All / Unread / Not replied / Starred / Archived`（文本形如 `Unread (11)`）；点 Unread 可只留未读会话（tab 也是真实点击才生效）。
- 陷阱：`[class*="messageRow"]` 会**同时命中列表项**（列表项内部也用了该 class），不能拿它找聊天消息。

## 打开会话（关键坑）

- 必须 `locator.click()`（Playwright 真实输入事件）；`evaluate("el.click()")` 原生 click **无效** → 右侧永远显示 "No chat selected."。
- 点开后聊天窗在右侧（left>450, width>1000）。
- `[class*="chatRoomContainer"]` 同时包含列表 + 聊天窗；选择器要限定在 `[class*="chatRoom--"]` 内，或直接用 chatd-* 独有 class。

## 聊天消息结构（TikTok chatd 组件）

| 内容 | 选择器 |
|---|---|
| 消息行 | `.chatd-message` |
| 方向 | `chatd-message--right`=我方(Nice M)；`chatd-message--left`=对方 |
| 时间 | `.chatd-time`（仅部分消息有，带 `chatd-message--hasTime`） |
| 发送者 | `.chatd-message-userName`（带 `hide` class 时隐藏） |
| 文本气泡 | `.chatd-bubble`，正文在 `pre.index-module__content--QKRoB`；`chatd-bubble--self`=我方，`chatd-bubble--other`=对方 |
| 系统消息 | `.index-module__messageSystem--gCY1D > .index-module__messageSystemContent--rycqo`（如 "1 products added to showcase"，无方向） |
| 合作邀请卡片 | `chatd-message-body-info-message` 内 `w-[328px]` 容器（含 "Invitation to Collaborate N"、产品数、价格如 $1.54/$3.96/$5.50/$5.06） |

## 抓取流程

1. 连接 CDP → 复用已加载页面（URL 不对才 goto）。
2. 轮询等 `Unread (N)` 出现。
3. 从列表收集未读会话名单（名字 + 未读数）。
4. 逐个：按名字匹配 `contactCard` → `locator.click()` → `wait_for_selector('.chatd-message')` + 再等 ~3.5s（消息异步加载）→ 提取全部 `.chatd-message`（时间/方向/类型/内容）→ 下一个。
5. 输出 JSON：每会话 `{header, count, messages: [{time, sender, type: text_self|text_other|system|card, content}]}`。

可复用脚本：`scripts/grab_im_unread.py`（改 TOP 常量即可跑）。

## 备注

- 点开会话会把未读清零（正常行为，读取即已读）。
- 超过 365 天的消息不提供（聊天窗顶部有提示 "Messages older than 365 days are not available."）。
- 系统消息（加购橱窗）语言随创作者地区：英文 "N products added to showcase" / 西语 "N productos agregados a la vitrina"。
