#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

sudo cp ${SCRIPT_DIR}/nginx/cloak-browser /etc/nginx/sites-available

sudo ln -s /etc/nginx/sites-available/cloak-browser /etc/nginx/sites-enabled/cloak-browser

sudo nginx -t && sudo systemctl reload nginx