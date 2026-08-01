#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

sudo cp ${SCRIPT_DIR}/tk-gateway /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/tk-gateway /etc/nginx/sites-enabled/tk-gateway

sudo nginx -t && sudo systemctl reload nginx