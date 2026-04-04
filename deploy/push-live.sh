#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-live}"
TARGET_BRANCH="${2:-live}"

git push "$REMOTE" "HEAD:refs/heads/$TARGET_BRANCH"
