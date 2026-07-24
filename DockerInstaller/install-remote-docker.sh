#!/bin/bash

set -e

SCRIPT_DIR="$(dirname "$0")"

source "$SCRIPT_DIR/.env"

ssh ${SERVER_NAME} "bash -s " < "$SCRIPT_DIR/install-docker-compose.sh"
