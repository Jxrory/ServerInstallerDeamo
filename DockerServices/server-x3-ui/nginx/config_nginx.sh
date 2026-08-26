#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
SITE_NAME="x3-ui"
DEFAULT_DOMAIN="makemoney2g.com"

# Ask for the base domain, defaulting to makemoney2g.com.
read -rp "请输入域名 (默认: ${DEFAULT_DOMAIN}): " DOMAIN
DOMAIN="${DOMAIN:-$DEFAULT_DOMAIN}"

# Basic validation: letters, digits, dots, hyphens.
if ! [[ "$DOMAIN" =~ ^[a-zA-Z0-9.-]+$ ]]; then
  echo "❌ 域名格式非法: $DOMAIN"
  exit 1
fi

CERT_DIR="/etc/letsencrypt/live/x3ui.${DOMAIN}"
CERT_KEY_DIR="/etc/letsencrypt/live/x3ui.${DOMAIN}"

# 证书前置检查(Let's Encrypt 签发后自动生成)
if [[ ! -f "${CERT_DIR}/fullchain.pem" || ! -f "${CERT_KEY_DIR}/privkey.pem" ]]; then
  echo "❌ 未找到证书: ${CERT_DIR}/fullchain.pem / ${CERT_KEY_DIR}/privkey.pem"
  echo "   本站为灰云直连域名, 需浏览器信任的证书。请先执行:"
  echo "   sudo certbot certonly --nginx -d x3ui.${DOMAIN}"
  exit 1
fi

# Render the site config with the given domain, then deploy.
TMP_CONF="$(mktemp)"
trap 'rm -f "$TMP_CONF"' EXIT
sed "s/makemoney2g\.com/${DOMAIN}/g" "${SCRIPT_DIR}/${SITE_NAME}" > "$TMP_CONF"

# Ensure the shared WebSocket upgrade map is installed (idempotent).
sudo cp "${SCRIPT_DIR}/websocket.conf" /etc/nginx/conf.d/websocket.conf

sudo cp "$TMP_CONF" "/etc/nginx/sites-available/${SITE_NAME}"
sudo ln -sf "/etc/nginx/sites-available/${SITE_NAME}" "/etc/nginx/sites-enabled/${SITE_NAME}"

sudo nginx -t && sudo systemctl reload nginx

echo "✅ 已部署 ${SITE_NAME}: https://x3ui.${DOMAIN}/ -> 127.0.0.1:2053"
