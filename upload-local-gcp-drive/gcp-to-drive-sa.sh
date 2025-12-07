#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --sa-dir <path> --src <remote:path> --dst <remote:path> [options]"
  echo "Options:"
  echo "  --limit SIZE         per-SA max transfer (e.g., 350G), default 350G"
  echo "  --transfers N        default 1"
  echo "  --checkers N         default 1"
  echo "  --chunk M            drive chunk size (e.g., 64M), default 64M"
  echo "  --bwlimit RATE       bandwidth limit (e.g., 200M), default 200M"
  echo "  --shared             include --drive-shared-with-me"
  echo "  --ignore-existing    skip files that already exist (default on)"
  echo "  --no-progress        hide progress"
  echo "  --dry-run            do not copy, just show what would be done"
  echo "  --log-file PATH      write rclone log to file"
  echo "  --log-level LEVEL    rclone log level (INFO, ERROR, DEBUG). default INFO"
  echo "  --sleep-sec N        sleep seconds before switching SA, default 5"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command not found: $1"; exit 1; }
}

SA_DIR=""
SRC=""
DST=""
LIMIT="350G"
TRANSFERS=1
CHECKERS=1
CHUNK="64M"
BWLIMIT="200M"
SHARED=false
IGNORE_EXISTING=true
PROGRESS=true
DRY_RUN=false
LOG_FILE=""
LOG_LEVEL="INFO"
SLEEP_SEC=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sa-dir)
      SA_DIR="$2"; shift 2;;
    --src)
      SRC="$2"; shift 2;;
    --dst)
      DST="$2"; shift 2;;
    --limit)
      LIMIT="$2"; shift 2;;
    --transfers)
      TRANSFERS="$2"; shift 2;;
    --checkers)
      CHECKERS="$2"; shift 2;;
    --chunk)
      CHUNK="$2"; shift 2;;
    --bwlimit)
      BWLIMIT="$2"; shift 2;;
    --shared)
      SHARED=true; shift;;
    --ignore-existing)
      IGNORE_EXISTING=true; shift;;
    --no-progress)
      PROGRESS=false; shift;;
    --dry-run)
      DRY_RUN=true; shift;;
    --log-file)
      LOG_FILE="$2"; shift 2;;
    --log-level)
      LOG_LEVEL="$2"; shift 2;;
    --sleep-sec)
      SLEEP_SEC="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1"; usage; exit 1;;
  esac
done

[[ -z "$SA_DIR" || -z "$SRC" || -z "$DST" ]] && { echo "--sa-dir, --src, and --dst are required"; usage; exit 1; }
[[ -d "$SA_DIR" ]] || { echo "Service Account directory not found: $SA_DIR"; exit 1; }

require_cmd rclone

mapfile -t SAS < <(ls -1 "$SA_DIR"/*.json 2>/dev/null || true)
[[ ${#SAS[@]} -gt 0 ]] || { echo "No Service Account JSON found in: $SA_DIR"; exit 1; }

for SA in "${SAS[@]}"; do
  echo ""
  echo "=========================================="
  echo "==> Using Service Account: $SA"
  echo "=========================================="

  export GOOGLE_APPLICATION_CREDENTIALS="$SA"

  ARGS=("copy" "$SRC" "$DST" "--transfers=${TRANSFERS}" "--checkers=${CHECKERS}" "--drive-chunk-size=${CHUNK}" "--fast-list" "--max-transfer" "$LIMIT" "--drive-stop-on-upload-limit" "--bwlimit" "$BWLIMIT" "--log-level=${LOG_LEVEL}")

  if [[ "$SHARED" == true ]]; then
    ARGS+=("--drive-shared-with-me")
  fi
  if [[ "$IGNORE_EXISTING" == true ]]; then
    ARGS+=("--ignore-existing")
  fi
  if [[ "$PROGRESS" == true ]]; then
    ARGS+=("--progress")
  fi
  if [[ "$DRY_RUN" == true ]]; then
    ARGS+=("--dry-run")
  fi
  if [[ -n "$LOG_FILE" ]]; then
    ARGS+=("--log-file=${LOG_FILE}")
  fi

  echo "Starting rclone copy with SA: $SA"
  rclone "${ARGS[@]}"
  STATUS=$?
  echo "Exit code: $STATUS"

  if [[ $STATUS -eq 0 ]]; then
    echo ">> Transfer complete. No more files."
    exit 0
  fi
  if [[ $STATUS -eq 8 ]]; then
    echo ">> Max-transfer reached (${LIMIT}). Switching SA..."
    sleep "$SLEEP_SEC"; continue
  fi
  if [[ $STATUS -eq 9 ]]; then
    echo ">> Upload limit exceeded for this SA. Switching..."
    sleep "$SLEEP_SEC"; continue
  fi
  if [[ $STATUS -eq 3 || $STATUS -eq 4 ]]; then
    echo ">> Rate limit (403) detected. Switching SA..."
    sleep "$SLEEP_SEC"; continue
  fi
  if [[ $STATUS -eq 7 ]]; then
    echo ">> 403 userRateLimitExceeded. Switching SA..."
    sleep "$SLEEP_SEC"; continue
  fi

  echo ">> Unhandled error. Stopping."
  continue
done

echo ">> All Service Accounts exhausted!"
echo ">> Add more SA for larger data."