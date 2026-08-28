# Feishu / Lark platform adapter notes

Adapter: `plugins/platforms/feishu/adapter.py` (bundled plugin, ~5.6k lines). Config: `platforms.feishu` in config.yaml; credentials/policy in `.env` (read at adapter startup — no hot reload).

## Environment variables & defaults (Hermes v0.18.x)

| Env var | Default | Effect |
|---|---|---|
| FEISHU_APP_ID / FEISHU_APP_SECRET | — | credentials; required |
| FEISHU_HOME_CHANNEL | — | home channel id |
| FEISHU_CONNECTION_MODE | `websocket` | long-connection mode (no public webhook needed) |
| FEISHU_GROUP_POLICY | **`allowlist`** | group admission: `open` / `allowlist` / `blacklist` / `admin_only` / `disabled` |
| FEISHU_ALLOWED_USERS | (empty) | comma-separated open_ids; used by allowlist policy AND as default group gate |
| FEISHU_ALLOW_ALL_USERS | `false` | **DM path only** — does NOT open group messages |
| GATEWAY_ALLOW_ALL_USERS | `false` | **DM path only** at adapter level (gateway pairing/auth layer is separate) |
| FEISHU_REQUIRE_MENTION | `true` | group messages must @bot (or @_all) |
| FEISHU_ALLOW_BOTS | `none` | `none` / `mentions` / `all` — bot-sender policy |
| FEISHU_BOT_OPEN_ID / FEISHU_BOT_USER_ID / FEISHU_BOT_NAME | — | bot identity for mention matching; auto-hydrated from `/open-apis/bot/v3/info` when unset |
| config.yaml `platforms.feishu.group_rules` | — | per-chat overrides: `{policy, allowlist, blacklist, require_mention}` |
| config.yaml `platforms.feishu.admins` | — | admin open_ids; bypass group policy |

## Admission flow for group messages

`_admit(sender, message)` → group path (`chat_type != "p2p"`):

1. `_allow_group_message()`: no per-group rule → policy = `default_group_policy or FEISHU_GROUP_POLICY` (default **allowlist**); allowlist = `FEISHU_ALLOWED_USERS` (default **empty set**).
   - `allowlist` policy + empty allowlist → `bool(sender_ids & ∅)` = **False → rejected**.
2. `require_mention` (default true): if message doesn't mention the bot → rejected.

Rejected events are dropped with `logger.debug("[Feishu] dropping inbound event: %s", reason)` — **invisible at INFO log level** (reasons: `self_echo`, `bots_disabled`, `bot_not_mentioned`, `group_policy_rejected`, `dm_policy_rejected`).

DM path differs: empty `FEISHU_ALLOWED_USERS` ⇒ pairing mode — DMs are forwarded to gateway intake for the pairing handshake (gateway auth layer fail-closes agent access until approved). So DMs can work while ALL group messages are dropped.

## Symptom match (observed 2026-08)

"@bot in a group gets no reply" while `gateway_state.json` says feishu `connected`, WS is up (`connected to wss://msg-frontier.feishu.cn`), `channel_directory.json` feishu list is empty, and logs are clean ⇒ group messages rejected by default allowlist-with-empty-allowlist. The gateway-side fix (below) is the primary suspect; console-side items are the secondary layer.

## Fixes

1. **Open group**: `.env` += `FEISHU_GROUP_POLICY=open` (all group members allowed; still need @mention). Restart gateway.
2. **Allowlist**: `.env` += `FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy` (users' open_ids), keep default policy.
3. **Per-group rules**: `config.yaml` → `platforms.feishu.group_rules.<chat_id> = {policy: open|allowlist|..., allowlist: [...], require_mention: bool}`.

## Console-side requirements (飞书开放平台) — verify when gateway config is correct but messages still don't arrive

- Permission scope **`im:message.group_at_msg`** (获取群组中@机器人的消息) for group @mention events; DMs need `im:message.p2p_msg`.
- Event subscription **`im.message.receive_v1`** enabled; in long-connection mode the console must show 长连接 (WebSocket) as the subscription method.
- The bot app must be added to the target group, and the app must be 启用 (published), not test-only.
- Messages without @mention are ignored while `FEISHU_REQUIRE_MENTION` is true.

## Restart after .env change

`.env` is read at adapter startup — restart the gateway service (see SKILL.md "Restarting the gateway in a containerized deployment"). In this container: `/package/admin/s6/command/s6-svc -r /run/service/gateway-default`; verify reconnect in `logs/gateway.log` and `gateway_state.json`.
