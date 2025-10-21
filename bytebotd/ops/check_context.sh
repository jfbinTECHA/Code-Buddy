#!/usr/bin/env bash
# ============================================================
#  Kilo / Bytebot Context & Dockerfile Sanity Check Utility
#  Usage: check_context.sh [--silent] [--json]
# ============================================================

set -e

PROJECT_ROOT="/home/sysop/bytebot/Code-Buddy"
DOCKERFILE_PATH="$PROJECT_ROOT/bytebotd/Dockerfile"

# --- Flags ---
SILENT=false
JSON=false
for arg in "$@"; do
  case "$arg" in
    --silent|-s) SILENT=true ;;
    --json|-j)   JSON=true ;;
  esac
done

# --- Internal state variables ---
STATUS_WORKDIR=false
STATUS_DIRS=false
STATUS_DOCKERFILE=false
MESSAGE=""

# --- Logging helpers ---
log() { $SILENT || $JSON || echo "$*"; }
fail_exit() {
  if $JSON; then
    printf '{"status":"FAIL","message":"%s"}\n' "$1"
  else
    echo "[FAIL] $1" >&2
  fi
  exit 1
}

# --- 1. Working directory check ---
CURRENT_DIR="$(pwd)"
if [[ "$CURRENT_DIR" != "$PROJECT_ROOT" ]]; then
  log "[WARN] Not in project root (currently: $CURRENT_DIR)"
  cd "$PROJECT_ROOT" || fail_exit "Could not change to $PROJECT_ROOT"
  STATUS_WORKDIR=true
else
  STATUS_WORKDIR=true
fi

# --- 2. Directory structure check ---
if [[ -d "$PROJECT_ROOT/shared" && -d "$PROJECT_ROOT/bytebotd" ]]; then
  STATUS_DIRS=true
else
  fail_exit "Missing required directories in build context."
fi

# --- 3. Dockerfile presence check ---
if [[ -f "$DOCKERFILE_PATH" && -s "$DOCKERFILE_PATH" ]]; then
  STATUS_DOCKERFILE=true
else
  fail_exit "Dockerfile missing or empty: $DOCKERFILE_PATH"
fi

# --- Output final result ---
if $JSON; then
  jq -n \
    --arg workdir "$STATUS_WORKDIR" \
    --arg dirs "$STATUS_DIRS" \
    --arg dockerfile "$STATUS_DOCKERFILE" \
    '{"status":"PASS","checks":{"workdir":$workdir,"directories":$dirs,"dockerfile":$dockerfile}}'
else
  $SILENT || echo "[PASS] All context checks completed successfully."
fi