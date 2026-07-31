#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

sudo cp ${SCRIPT_DIR}/nginx/bifrost /etc/nginx/sites-available

sudo ln -s /etc/nginx/sites-available/bifrost /etc/nginx/sites-enabled/bifrost

sudo nginx -t && sudo systemctl reload nginx