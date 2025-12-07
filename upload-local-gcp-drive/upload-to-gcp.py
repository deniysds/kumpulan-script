#!/usr/bin/env python3
import argparse, csv, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo
from google.cloud import storage
from google.api_core.retry import Retry
import time, math

TZ = ZoneInfo("Asia/Jakarta")

def iter_files(src: Path):
    if src.is_file():
        yield src
    else:
        for p in src.rglob("*"):
            if p.is_file():
                yield p

# Tuneables for flaky links
WRITE_TIMEOUT_SEC = 900          # 15 minutes per request
CHUNK_SIZE = 8 * 1024 * 1024     # 8 MiB chunks help on unstable networks
MAX_ATTEMPTS = 6                 # total attempts per file
BASE_BACKOFF = 2.0               # seconds (exponential)

def upload_one(client, bucket_name, local_path, dest_prefix, source_root):
    bucket = client.bucket(bucket_name)
    rel = local_path.relative_to(source_root) if source_root.is_dir() else local_path.name
    blob_name = f"{dest_prefix}{rel}".replace("\\", "/")
    blob = bucket.blob(blob_name)
    blob.chunk_size = CHUNK_SIZE  # force resumable, smaller writes

    retry_policy = Retry(  # retry transient errors incl. timeouts/connection resets
        initial=1.0, maximum=32.0, multiplier=2.0, deadline=WRITE_TIMEOUT_SEC + 60
    )

    start_total = time.perf_counter()
    size_bytes = local_path.stat().st_size

    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            start = time.perf_counter()
            # NOTE: timeout here is per HTTP request (per chunk), not the whole file
            blob.upload_from_filename(
                str(local_path),
                timeout=WRITE_TIMEOUT_SEC,
                retry=retry_policy
            )
            dur = time.perf_counter() - start_total
            mbps = (size_bytes / (1024*1024)) / dur if dur > 0 else 0.0
            ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
            return {
                "timestamp_local": ts,
                "source_path": str(local_path),
                "gcs_uri": f"gs://{bucket_name}/{blob_name}",
                "size_bytes": size_bytes,
                "duration_sec": round(dur, 3),
                "throughput_MBps": round(mbps, 2),
            }
        except Exception as e:
            last_err = e
            if attempt == MAX_ATTEMPTS:
                raise
            # exponential backoff with jitter
            sleep_s = BASE_BACKOFF * (2 ** (attempt - 1))
            sleep_s *= (0.75 + 0.5 * (time.perf_counter() % 1))  # cheap jitter
            print(f"[RETRY {attempt}/{MAX_ATTEMPTS-1}] {local_path} due to: {e}. Sleeping {sleep_s:.1f}s")
            time.sleep(sleep_s)

    # Should not reach here
    raise last_err

def main():
    ap = argparse.ArgumentParser(description="Upload to GCS with per-file time report")
    ap.add_argument("source", help="File or directory to upload")
    ap.add_argument("bucket", help="Target bucket name (without gs://)")
    ap.add_argument("--prefix", default="", help="Object key prefix inside the bucket (e.g., 'backup/')")
    ap.add_argument("--workers", type=int, default=4, help="Parallel upload workers")
    ap.add_argument("--log", default=None, help="CSV log path (default: ./logs/gcs_upload_<timestamp>.csv)")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        sys.exit(1)

    ts_name = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    log_dir = Path("./logs"); log_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log) if args.log else log_dir / f"gcs_upload_{ts_name}.csv"

    client = storage.Client()
    files = list(iter_files(source))
    if not files:
        print("No files to upload.")
        return

    # Ensure prefix ends with / if provided and not already
    prefix = args.prefix
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    print(f"Uploading {len(files)} file(s) to gs://{args.bucket}/{prefix} ...")
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_local","source_path","gcs_uri","size_bytes","duration_sec","throughput_MBps"])
        writer.writeheader()

        successes = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(upload_one, client, args.bucket, p, prefix, source): p for p in files}
            for fut in as_completed(futs):
                p = futs[fut]
                try:
                    row = fut.result()
                    writer.writerow(row)
                    successes += 1
                    print(f"[OK] {p} -> {row['gcs_uri']} ({row['duration_sec']}s, {row['throughput_MBps']} MB/s)")
                except Exception as e:
                    print(f"[FAIL] {p}: {e}", file=sys.stderr)

    print(f"Done. Success: {successes}/{len(files)}. Log: {log_path}")

if __name__ == "__main__":
    main()