#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

# Ensure the shared WebSocket upgrade map is installed (idempotent).
sudo cp ${SCRIPT_DIR}/websocket.conf /etc/nginx/conf.d/websocket.conf

sudo cp ${SCRIPT_DIR}/bifrost /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/bifrost /etc/nginx/sites-enabled/bifrost

sudo nginx -t && sudo systemctl reload nginx