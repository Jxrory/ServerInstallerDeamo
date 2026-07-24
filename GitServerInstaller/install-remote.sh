#!/bin/bash

set -e

SCRIPT_DIR="$(dirname "$0")"

source "$SCRIPT_DIR/.env"
source "$SCRIPT_DIR/../.env"

ssh ${SERVER_NAME} \
"export \
GIT_USER='$GIT_USER' \
GIT_HOME='$GIT_HOME' \
GIT_REPO_BASE='$GIT_REPO_BASE'; \
bash -s " \
< "$SCRIPT_DIR/install.sh"