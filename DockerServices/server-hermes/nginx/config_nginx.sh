#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

sudo cp ${SCRIPT_DIR}/nginx/hermes-gateway /etc/nginx/sites-available
sudo ln -s /etc/nginx/sites-available/hermes-gateway /etc/nginx/sites-enabled/hermes-gateway

sudo cp ${SCRIPT_DIR}/nginx/hermes-dashboard /etc/nginx/sites-available
sudo ln -s /etc/nginx/sites-available/hermes-dashboard /etc/nginx/sites-enabled/hermes-dashboard

sudo nginx -t && sudo systemctl reload nginx