#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
SITE_NAME="gogs"
DEFAULT_DOMAIN="makemoney2g.com"

# Ask for the base domain, defaulting to makemoney2g.com.
read -rp "请输入域名 (默认: ${DEFAULT_DOMAIN}): " DOMAIN
DOMAIN="${DOMAIN:-$DEFAULT_DOMAIN}"

# Basic validation: letters, digits, dots, hyphens.
if ! [[ "$DOMAIN" =~ ^[a-zA-Z0-9.-]+$ ]]; then
  echo "❌ 域名格式非法: $DOMAIN"
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

echo "✅ 已部署 ${SITE_NAME}: https://git.${DOMAIN}/ -> 127.0.0.1:4647"
