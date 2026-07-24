#!/bin/bash

set -e

SCRIPT_DIR="$(dirname "$0")"

source "$SCRIPT_DIR/.env"
source "$SCRIPT_DIR/../.env"


REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "用法: $0 repo-name"
    exit 1
fi


ssh ${SERVER_NAME} \
"export \
GIT_USER='$GIT_USER' \
GIT_HOME='$GIT_HOME' \
GIT_REPO_BASE='$GIT_REPO_BASE'; \
bash -s '$REPO_NAME'" \
< "$SCRIPT_DIR/delete-repo.sh"