#!/bin/bash

SADIR="/home/daeng_deni/sa"
SAS=($SADIR/*.json)

SRC="gcs:transit_bucket_ysds/bawang_putih_prima_UGM"
DST="gdrive_sa:01_Data Mentah/ugm/prima/bawang_putih"
LIMIT="350G"

for SA in "${SAS[@]}"; do
    echo ""
    echo "=========================================="
    echo "==> Using Service Account: $SA"
    echo "=========================================="

    export GOOGLE_APPLICATION_CREDENTIALS="$SA"

    rclone copy "$SRC" "$DST" \
        --transfers=1 \
        --checkers=1 \
        --drive-chunk-size=64M \
        --fast-list \
        --drive-shared-with-me \
        --ignore-existing \
        --max-transfer $LIMIT \
        --drive-stop-on-upload-limit \
        --bwlimit 200M \
        --verbose \
        --progress

    STATUS=$?

    echo "Exit code: $STATUS"

    # === STATUS HANDLING ===
    if [ $STATUS -eq 0 ]; then
        echo ">> Transfer complete. No more files."
        exit 0
    fi

    # Max-transfer reached → ganti SA
    if [ $STATUS -eq 8 ]; then
        echo ">> Max-transfer reached ($LIMIT). Switching SA..."
        sleep 5
        continue
    fi

    # Upload limit (403 quota exceeded)
    if [ $STATUS -eq 9 ]; then
        echo ">> Upload limit exceeded for this SA. Switching..."
        sleep 5
        continue
    fi

    # Generic rate-limit error
    if [ $STATUS -eq 3 ] || [ $STATUS -eq 4 ]; then
        echo ">> Rate limit (403) detected. Switching SA..."
        sleep 5
        continue
    fi

    # ❗ INI FIX PENTING UNTUK KASUS ANDA
   # userRateLimitExceeded → exit code 7
   if [ $STATUS -eq 7 ]; then
       echo ">> 403 userRateLimitExceeded. Switching SA..."
       sleep 5
       continue
   fi

   # Error bukan karena limit → berhenti
   echo ">> Unhandled error. Stopping."
   continue
done

echo ">> All Service Accounts exhausted!"
echo ">> Add more SA for larger data."