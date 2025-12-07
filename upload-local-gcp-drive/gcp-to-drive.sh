#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --src <remote:path> --dst <remote:path> [options]"
  echo "Options:"
  echo "  --transfers N        default 16"
  echo "  --checkers N         default 8"
  echo "  --chunk M            drive chunk size (e.g., 64M), default 64M"
  echo "  --shared             include --drive-shared-with-me"
  echo "  --ignore-existing    skip files that already exist (default on)"
  echo "  --no-progress        hide progress"
  echo "  --dry-run            do not copy, just show what would be done"
  echo "  --log-file PATH      write rclone log to file"
  echo "  --log-level LEVEL    rclone log level (INFO, ERROR, DEBUG). default INFO"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command not found: $1"; exit 1; }
}

SRC=""
DST=""
TRANSFERS=16
CHECKERS=8
CHUNK="64M"
SHARED=false
IGNORE_EXISTING=true
PROGRESS=true
DRY_RUN=false
LOG_FILE=""
LOG_LEVEL="INFO"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src)
      SRC="$2"; shift 2;;
    --dst)
      DST="$2"; shift 2;;
    --transfers)
      TRANSFERS="$2"; shift 2;;
    --checkers)
      CHECKERS="$2"; shift 2;;
    --chunk)
      CHUNK="$2"; shift 2;;
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
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1"; usage; exit 1;;
  esac
done

[[ -z "$SRC" || -z "$DST" ]] && { echo "--src and --dst are required"; usage; exit 1; }

require_cmd rclone

ARGS=("copy" "$SRC" "$DST" "--transfers=${TRANSFERS}" "--checkers=${CHECKERS}" "--drive-chunk-size=${CHUNK}" "--log-level=${LOG_LEVEL}")

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

echo "Starting rclone copy: $SRC -> $DST"
echo "transfers=${TRANSFERS} checkers=${CHECKERS} chunk=${CHUNK} log=${LOG_LEVEL} shared=${SHARED}"
rclone "${ARGS[@]}"
echo "Completed rclone copy: $SRC -> $DST"