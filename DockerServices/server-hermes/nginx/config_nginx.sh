#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

# Install the shared WebSocket upgrade map exactly once (http context).
sudo cp ${SCRIPT_DIR}/websocket.conf /etc/nginx/conf.d/websocket.conf

sudo cp ${SCRIPT_DIR}/hermes-gateway /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/hermes-gateway /etc/nginx/sites-enabled/hermes-gateway

sudo cp ${SCRIPT_DIR}/hermes-dashboard /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/hermes-dashboard /etc/nginx/sites-enabled/hermes-dashboard

sudo nginx -t && sudo systemctl reload nginx