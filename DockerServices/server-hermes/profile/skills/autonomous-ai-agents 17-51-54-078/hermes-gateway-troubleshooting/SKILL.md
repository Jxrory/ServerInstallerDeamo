---
name: hermes-gateway-troubleshooting
description: "Troubleshoot Hermes messaging gateway issues: bot not responding on a platform (Feishu/Lark, Slack, Discord, Telegram...), messages silently dropped despite 'connected' status, and gateway restart mechanics in containerized/s6 deployments."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, troubleshooting, messaging, feishu, lark, s6, docker, platform-adapter]
    related_skills: [hermes-agent]
---

# Hermes Gateway Troubleshooting

Use when a Hermes bot on a messaging platform (Feishu/Lark, Slack, Discord, Telegram, Teams...) isn't responding — messages ignored, @mentions unanswered, platform shows "connected" but nothing happens — or when the gateway must be restarted in a containerized deployment.

The bundled `hermes-agent` skill covers general Hermes ops; this skill is the debugging playbook for gateway/platform message-flow failures and container restart mechanics.

## Key paths (under $HERMES_HOME, e.g. /opt/data)

| Path | What it tells you |
|---|---|
| `config.yaml` | platform enablement (`platforms.<name>.enabled`) |
| `.env` | platform credentials + policy env vars |
| `logs/gateway.log` | gateway lifecycle, adapter connect/disconnect (INFO) |
| `logs/errors.log`, `logs/agent.log` | adapter errors, lazy-install traces |
| `gateway_state.json` | per-platform adapter state (connected/disconnected + error) |
| `gateway.pid` | gateway process PID and argv |
| `channel_directory.json` | registered chat channels — **empty list for a platform = no message has ever been admitted** |

## Diagnosis workflow

1. **Locate the binary**: `hermes` may not be on PATH (e.g. `/opt/hermes/bin/hermes`, venv at `/opt/hermes/.venv/bin/hermes`). Check `$HERMES_HOME` and `which -a hermes` / `find / -maxdepth 4 -name hermes`.
2. **Is the platform connected?** Read `gateway_state.json` → `platforms.<name>.state`. "connected" means credentials work and transport (WebSocket/webhook) is up — it does NOT mean messages are accepted.
3. **Read the adapter logs**: `grep -i <platform> logs/*.log`. A "Connected in websocket mode" / "connected to wss://..." line confirms transport.
4. **Are messages arriving at all?** Empty `channel_directory.json` + no inbound traces ⇒ either events aren't delivered from the platform (console-side subscription/permissions) or the adapter is silently dropping them.
5. **Read the adapter's admission code**: `plugins/platforms/<name>/adapter.py` — find `_admit` / admission-gate logic, the policy env vars it reads, and their defaults. This is where silent message drops live.
6. **Audit `.env` keys** (`cut -d= -f1 .env`, values redacted) against the env vars the adapter reads.

## Pitfalls

- **Admission policies default to restrictive.** Platform adapters commonly default to allowlist/pairing modes. With an empty allowlist, EVERY message is rejected — and rejections are often logged at DEBUG level only, so INFO logs look clean. Symptom: "connected" + zero channels + no logs. Check the adapter source for `_admit` / `_allow_group_message` style gates and env-var defaults (`*_GROUP_POLICY`, `*_ALLOWED_USERS`, `require_mention`).
- **`*_ALLOW_ALL_USERS`-style env vars may only affect DMs.** In the Feishu adapter, `FEISHU_ALLOW_ALL_USERS` / `GATEWAY_ALLOW_ALL_USERS` gate only `not is_group` (DM) traffic; group messages are gated separately by `FEISHU_GROUP_POLICY` / `FEISHU_ALLOWED_USERS`. Verify per-adapter before assuming a global allow-all exists.
- **Gateway restart from inside the gateway process is blocked**: `hermes gateway restart` refuses with "cannot restart or stop the gateway from inside the gateway process" (SIGTERM would kill the caller). In s6/docker deployments, find which s6 service owns the gateway and restart that service only (see below).
- **Platform console-side requirements are a second layer** the gateway can't verify: event subscription enabled (`im.message.receive_v1` for Feishu), message-read permission scope, bot added to the target group, app published. State these as "verify in console" items when gateway config looks correct.
- **Rejections are logged at DEBUG**: to observe drops in real time, raise the adapter's log level (or add temporary debug logging) before testing — don't conclude "no messages arrive" from clean INFO logs.

## Restarting the gateway in a containerized (s6-overlay) deployment

1. Identify service ownership: `ps -o pid,ppid,cmd -p <gateway_pid>` → PPID is the s6-supervise process; `ps -ef | grep s6-supervise` maps it to a service dir under `/run/service/`.
2. Check your own session isn't under the same service (TUI sessions often run under a `dashboard` service while the messaging gateway is e.g. `gateway-default`) — restarting the gateway service then does NOT kill the session.
3. Restart: `/package/admin/s6/command/s6-svc -r /run/service/<service-name>` (s6-svc is usually not on PATH).
4. Verify: new gateway PID (`ps -o pid,etime,cmd -C python3 | grep "gateway run"`), `gateway_state.json` platforms back to "connected", adapter reconnect log line.

## Platform-specific references

- `references/feishu-platform.md` — Feishu/Lark adapter admission policy, env vars & defaults, fix options, console-side requirements.
